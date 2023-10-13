from pathlib import Path
from typing import Literal
from datetime import datetime

import jinja2
from pydantic import BaseModel, root_validator
from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from nonebot_bison.post import Post
from nonebot_bison.theme import (
    AbstractTheme,
    ThemeRenderError,
    ThemeRenderUnsupportError,
    check_htmlrender_plugin_enable,
)


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


class CeobeCard(BaseModel):
    info: CeobeInfo
    content: CeoboContent
    qr: str | None


class CeobeCanteenTheme(AbstractTheme):
    """小刻食堂 分享卡片风格主题

    需要安装`nonebot_plugin_htmlrender`插件
    """

    name: Literal["ceobecanteen"] = "ceobecanteen"

    template_path: Path = Path(__file__).parent / "templates"
    template_name: str = "announce.html.jinja"

    def parse(self, post: Post) -> CeobeCard:
        """解析 Post 为 CeobeCard"""
        if not post.nickname:
            raise ThemeRenderUnsupportError("post.nickname is None")
        if not post.timestamp:
            raise ThemeRenderUnsupportError("post.timestamp is None")
        info = CeobeInfo(
            datasource=post.nickname, time=datetime.fromtimestamp(post.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        )

        head_pic = post.images[0] if post.images else None
        if head_pic is not None and not isinstance(head_pic, str):
            raise ThemeRenderUnsupportError("post.images[0] is not str")

        content = CeoboContent(image=head_pic, text=post.content)
        return CeobeCard(info=info, content=content, qr=post.url)  # TODO： 这里需要链接转qr码图片，暂时先用链接代替

    async def render(self, post: Post) -> list[MessageSegmentFactory]:
        ceobe_card = self.parse(post)
        check_htmlrender_plugin_enable()
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
        if post.images:
            msgs.extend(map(Image, post.images))
        if post.url:
            msgs.append(Text(post.url))
        return msgs
