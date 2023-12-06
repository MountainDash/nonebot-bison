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
    author: str | None

    @root_validator
    def check(cls, values):
        if values["image"] is None and values["text"] is None:
            raise ValueError("image and text cannot be both None")
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

    async def parse(self, post: "Post") -> CeobeCard:
        """解析 Post 为 CeobeCard"""
        if not post.nickname:
            raise ThemeRenderUnsupportError("post.nickname is None")
        if not post.timestamp:
            raise ThemeRenderUnsupportError("post.timestamp is None")
        info = CeobeInfo(
            datasource=post.nickname, time=datetime.fromtimestamp(post.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        )

        async def merge_pics(images: list[str | bytes] | None, client: AsyncClient) -> list[str | bytes] | None:
            if images and is_pics_mergable(images):
                pics = await pic_merge(list(images), client)
                return list(pics)
            return images

        post.images = await merge_pics(post.images, post.platform.client)
        head_pic = post.images[0] if post.images else None
        if head_pic is not None and not isinstance(head_pic, str):
            head_pic = web_embed_image(head_pic)

        content = CeoboContent(image=head_pic, text=post.content)

        retweet: CeoboRetweet | None = None
        if post.repost:
            post.repost.images = await merge_pics(post.repost.images, post.platform.client)
            head_retweet_pic = post.repost.images[0] if post.repost.images else None
            post.repost.nickname = "转发自 @" + post.repost.nickname + ":"
            retweet = CeoboRetweet(image=head_retweet_pic, content=post.repost.content, author=post.repost.nickname)

        content = CeoboRetweet(image=head_pic, text=post.content)
        return CeobeCard(
            info=info,
            content=content,
            qr=web_embed_image(convert_to_qr(post.url or "No URL", back_color=(240, 236, 233))),
            retweet=retweet,
        )

    async def render(self, post: "Post") -> list[MessageSegmentFactory]:
        ceobe_card = await self.parse(post)
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
            msgs.extend(map(Image, post.images))

        return msgs
