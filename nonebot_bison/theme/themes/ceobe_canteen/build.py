import base64
from collections.abc import Sequence
from datetime import datetime
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import anyio
from httpx import AsyncClient
import jinja2
from nonebot_plugin_saa import Image, MessageSegmentFactory, Text
from PIL import Image as PILImage
from pydantic import BaseModel
from yarl import URL

from nonebot_bison.compat import model_validator
from nonebot_bison.theme import Theme, ThemeRenderError, ThemeRenderUnsupportError
from nonebot_bison.theme.utils import convert_to_qr, web_embed_image
from nonebot_bison.utils import is_pics_mergable, pic_merge

if TYPE_CHECKING:
    from nonebot_bison.post import Post


@lru_cache
async def embed_image_as_data_url(image_path: Path) -> str:
    """读取图片文件并返回base64数据URL字符串

    Args:
        image_path: 图片文件路径

    Returns:
        base64格式的data URL字符串
    """
    if not image_path.exists():
        return ""

    async with await anyio.open_file(image_path, "rb") as f:
        image_data = base64.b64encode(await f.read()).decode()
        return f"data:image/png;base64,{image_data}"


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

    image: str | None = None
    text: str


class CeoboRetweet(BaseModel):
    """卡片的转发部分

    author: 原作者
    image: 图片链接
    content: 文字内容
    """

    image: str | None
    content: str | None
    author: str

    @model_validator(mode="before")
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

        http_client = await post.platform.ctx.get_client_for_static()
        images: list[str | bytes | Path | BytesIO] = []
        if post.images:
            images = await self.merge_pics(post.images, http_client)

        content = CeoboContent(text=await post.get_content())

        retweet: CeoboRetweet | None = None
        if post.repost:
            repost_head_pic: str | None = None
            if post.repost.images:
                repost_images = await self.merge_pics(post.repost.images, http_client)
                repost_head_pic = self.extract_head_pic(repost_images)
                images.extend(repost_images)

            repost_nickname = f"@{post.repost.nickname}:" if post.repost.nickname else ""
            retweet = CeoboRetweet(
                image=repost_head_pic, content=await post.repost.get_content(), author=repost_nickname
            )

        return (
            CeobeCard(
                info=info,
                content=content,
                qr=web_embed_image(convert_to_qr(post.url or "No URL", back_color=(240, 236, 233))),
                retweet=retweet,
            ),
            images,
        )

    @staticmethod
    async def merge_pics(
        images: Sequence[str | bytes | Path | BytesIO],
        client: AsyncClient,
    ) -> list[str | bytes | Path | BytesIO]:
        if is_pics_mergable(images):
            pics = await pic_merge(images, client)
        else:
            pics = images
        return list(pics)

    @staticmethod
    def extract_head_pic(pics: list[str | bytes | Path | BytesIO]) -> str:
        head_pic = web_embed_image(pics[0]) if not isinstance(pics[0], str) else pics[0]
        return head_pic

    @staticmethod
    def card_link(head_pic: PILImage.Image, card_body: PILImage.Image) -> PILImage.Image:
        """将头像与卡片合并"""

        def resize_image(img: PILImage.Image, size: tuple[int, int]) -> PILImage.Image:
            return img.resize(size)

        # 统一图片宽度
        head_pic_w, head_pic_h = head_pic.size
        card_body_w, card_body_h = card_body.size

        if head_pic_w > card_body_w:
            head_pic = resize_image(head_pic, (card_body_w, int(head_pic_h * card_body_w / head_pic_w)))
        else:
            card_body = resize_image(card_body, (head_pic_w, int(card_body_h * head_pic_w / card_body_w)))

        # 合并图片
        card = PILImage.new("RGBA", (head_pic.width, head_pic.height + card_body.height))
        card.paste(head_pic, (0, 0))
        card.paste(card_body, (0, head_pic.height))
        return card

    async def render(self, post: "Post") -> list[MessageSegmentFactory]:
        ceobe_card, merged_images = await self.parse(post)

        need_card_link: bool = True
        head_pic = None

        # 如果没有 post.images，则全部都是转发里的图片，不需要头图
        if post.images:
            match merged_images[0]:
                case bytes():
                    head_pic = merged_images[0]
                    merged_images = merged_images[1:]
                case BytesIO():
                    head_pic = merged_images[0].getvalue()
                    merged_images = merged_images[1:]
                case str(s) if URL(s).scheme in ("http", "https"):
                    ceobe_card.content.image = merged_images[0]
                    need_card_link = False
                case Path():
                    ceobe_card.content.image = merged_images[0].as_uri()
                    need_card_link = False
                case _:
                    raise ThemeRenderError(f"Unknown image type: {type(merged_images[0])}")

        from nonebot_plugin_htmlrender import get_new_page

        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_path),
            enable_async=True,
        )
        template = template_env.get_template(self.template_name)

        # 获取嵌入的图片数据
        bison_logo_data = await embed_image_as_data_url(self.template_path / "bison_logo.png")
        ceobe_logo_data = await embed_image_as_data_url(self.template_path / "ceobecanteen_logo.png")

        html = await template.render_async(card=ceobe_card, bison_logo=bison_logo_data, ceobe_logo=ceobe_logo_data)
        pages = {
            "device_scale_factor": 2,
            "viewport": {"width": 512, "height": 455},
            "base_url": self.template_path.as_uri(),
        }
        try:
            async with get_new_page(**pages) as page:
                await page.goto("about:blank")
                await page.set_content(html)
                await page.wait_for_timeout(1)
                card_body = await page.locator("#ceobecanteen-card").screenshot(
                    type="jpeg",
                    quality=90,
                )
        except Exception as e:
            raise ThemeRenderError(f"Render error: {e}") from e

        msgs: list[MessageSegmentFactory] = []
        if need_card_link and head_pic:
            card_pil = self.card_link(
                head_pic=PILImage.open(BytesIO(head_pic)),
                card_body=PILImage.open(BytesIO(card_body)),
            )
            card_data = BytesIO()
            card_pil.save(card_data, format="PNG")
            msgs.append(Image(card_data.getvalue()))
        else:
            msgs.append(Image(card_body))

        text = f"来源: {post.platform.name} {post.nickname or ''}\n"
        if post.url:
            text += f"详情: {post.url}"
        msgs.append(Text(text))

        pics_group: list[Sequence[str | bytes | Path | BytesIO]] = []
        if post.images:
            pics_group.append(post.images)
        if post.repost and post.repost.images:
            pics_group.append(post.repost.images)

        client = await post.platform.ctx.get_client_for_static()
        for pics in pics_group:
            if is_pics_mergable(pics):
                pics = await pic_merge(list(pics), client)
            msgs.extend(map(Image, pics))

        return msgs
