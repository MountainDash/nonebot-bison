from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from nonebot_plugin_saa import Image, MessageSegmentFactory, Text

from nonebot_bison.theme import Theme, ThemeRenderError, ThemeRenderUnsupportError
from nonebot_bison.theme.utils import web_embed_image
from nonebot_bison.utils import text_fletten

if TYPE_CHECKING:
    from nonebot_bison.platform.arknights import ArknightsPost


@dataclass
class ArkData:
    announce_title: str
    content: str
    banner_image_url: str | Path | None


class ArknightsTheme(Theme):
    """Arknights 公告风格主题

    需要安装`nonebot_plugin_htmlrender`插件
    """

    name: Literal["arknights"] = "arknights"
    need_browser: bool = True

    template_path: Path = Path(__file__).parent / "templates"
    template_name: str = "announce.html.jinja"

    async def render(self, post: "ArknightsPost"):
        from nonebot_bison.theme.render_helper import template_to_pic

        if not post.title:
            raise ThemeRenderUnsupportError("标题为空")

        banner = post.images[0] if post.images else None

        match banner:
            case bytes() | BytesIO():
                banner = web_embed_image(banner)
            case str() | Path() | None:
                pass
            case _:
                raise ThemeRenderUnsupportError(
                    f"图片类型错误, 期望 str | Path | bytes | BytesIO | None, 实际为 {type(banner)}"
                )
        ark_data = ArkData(
            announce_title=text_fletten(post.title),
            content=await post.get_content(),
            banner_image_url=banner,
        )

        try:
            announce_pic = await template_to_pic(
                template_path=self.template_path.as_posix(),
                template_name=self.template_name,
                templates={
                    "data": ark_data,
                },
                pages={
                    "viewport": {"width": 600, "height": 100},
                },
            )
        except Exception as e:
            raise ThemeRenderError(f"渲染文本失败: {e}")
        msgs: list[MessageSegmentFactory] = []
        msgs.append(Image(announce_pic))

        if post.url:
            msgs.append(Text(f"前往:{post.url}"))
        if post.images:
            msgs.extend(Image(img) for img in post.images[1:])

        return msgs
