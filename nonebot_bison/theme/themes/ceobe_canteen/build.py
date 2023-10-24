from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING, Literal

import jinja2
from httpx import AsyncClient
from pydantic import BaseModel, root_validator
from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from nonebot_bison.utils import pic_merge, is_pics_mergable
from nonebot_bison.theme.utils import convert_to_qr, web_embed_image
from nonebot_bison.theme import Theme, ThemeRenderError, ThemeRenderUnsupportError

if TYPE_CHECKING:
    from nonebot_bison.post import Post


class CeobeInfo(BaseModel):
    """卡片的信息部分

    datasource: 数据来源

    time: 时间
    """

    datasource: str
    time: str


class CeoboContent(BaseModel):
    """卡片的内容部分

    image: 图片链接
    text: 文字内容
    """

    image: str | None
    text: str | None

    @root_validator
    def check(cls, values):
        if values["image"] is None and values["text"] is None:
            raise ValueError("image and text cannot be both None")
        return values


class CeoboRetweet(BaseModel):
    """卡片的转发部分

    author: 原作者
    image: 图片链接
    content: 文字内容
    """

    image: str | None
    content: str | None
    author: str

    @root_validator
    def check(cls, values):
        if values["image"] is None and values["content"] is None:
            raise ValueError("image and content cannot be both None")
        return values


class CeobeCard(BaseModel):
    info: CeobeInfo
    content: CeoboContent
    qr: str | None
    retweet: CeoboRetweet | None


class CeobeCanteenTheme(Theme):
    """小刻食堂 分享卡片风格主题

    需要安装`nonebot_plugin_htmlrender`插件
    """

    name: Literal["ceobecanteen"] = "ceobecanteen"
    need_browser: bool = True

    template_path: Path = Path(__file__).parent / "templates"
    template_name: str = "ceobe_canteen.html.jinja"

    async def parse(self, post: "Post") -> tuple[CeobeCard, list[str | bytes | Path | BytesIO]]:
        """解析 Post 为 CeobeCard与处理好的图片列表"""
        if not post.nickname:
            raise ThemeRenderUnsupportError("post.nickname is None")
        if not post.timestamp:
            raise ThemeRenderUnsupportError("post.timestamp is None")
        info = CeobeInfo(
            datasource=post.nickname, time=datetime.fromtimestamp(post.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        )

        async def merge_and_extract_head_pic(
            images: list[str | bytes | Path | BytesIO], client: AsyncClient
        ) -> tuple[list[str | bytes | Path | BytesIO], str]:
            if is_pics_mergable(images):
                pics = await pic_merge(images, client)
            else:
                pics = images

            head_pic = web_embed_image(pics[0]) if not isinstance(pics[0], str) else pics[0]

            return list(pics), head_pic

        images: list[str | bytes | Path | BytesIO] = []
        head_pic: str | bytes | None = None
        if post.images:
            images, head_pic = await merge_and_extract_head_pic(post.images, post.platform.client)

        content = CeoboContent(image=head_pic, text=post.content)

        retweet: CeoboRetweet | None = None
        if post.repost:
            repost_head_pic: str | None = None
            if post.repost.images:
                repost_images, repost_head_pic = await merge_and_extract_head_pic(
                    post.repost.images, post.platform.client
                )
                images.extend(repost_images)

            repost_nickname = f"@{post.repost.nickname}:" if post.repost.nickname else ""
            retweet = CeoboRetweet(image=repost_head_pic, content=post.repost.content, author=repost_nickname)

        return (
            CeobeCard(
                info=info,
                content=content,
                qr=web_embed_image(convert_to_qr(post.url or "No URL", back_color=(240, 236, 233))),
                retweet=retweet,
            ),
            images,
        )

    async def render(self, post: "Post") -> list[MessageSegmentFactory]:
        ceobe_card, merged_images = await self.parse(post)
        from nonebot_plugin_htmlrender import get_new_page

        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_path),
            enable_async=True,
        )
        template = template_env.get_template(self.template_name)
        html = await template.render_async(card=ceobe_card)
        pages = {
            "viewport": {"width": 1000, "height": 3000},
            "base_url": self.template_path.as_uri(),
        }
        try:
            async with get_new_page(**pages) as page:
                await page.goto(self.template_path.as_uri())
                await page.set_content(html)
                await page.wait_for_timeout(1)
                img_raw = await page.locator("#ceobecanteen-card").screenshot(
                    type="png",
                )
        except Exception as e:
            raise ThemeRenderError(f"Render error: {e}") from e
        msgs: list[MessageSegmentFactory] = [Image(img_raw)]

        text = f"来源: {post.platform.name} {post.nickname or ''}\n"
        if post.url:
            text += f"详情: {post.url}"
        msgs.append(Text(text))

        if post.images:
            msgs.extend(map(Image, merged_images))

        return msgs
