from pathlib import Path
from typing import Literal
from dataclasses import dataclass

from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from nonebot_bison.types import PostHeader, PostPayload
from nonebot_bison.theme import Theme, ThemeRenderError, ThemeRenderUnsupportError


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

    async def render(self, header: PostHeader, payload: PostPayload):
        from nonebot_plugin_htmlrender import template_to_pic

        if not payload.title:
            raise ThemeRenderUnsupportError("标题为空")
        if payload.images and len(payload.images) > 1:
            raise ThemeRenderUnsupportError("图片数量大于1")

        banner = payload.images[0] if payload.images else None

        if banner is not None and not isinstance(banner, str | Path):
            raise ThemeRenderUnsupportError(f"图片类型错误, 期望 str 或 Path, 实际为 {type(banner)}")

        ark_data = ArkData(
            announce_title=payload.title,
            content=payload.content,
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
                    "base_url": self.template_path.as_uri(),
                },
            )
        except Exception as e:
            raise ThemeRenderError(f"渲染文本失败: {e}")
        msgs: list[MessageSegmentFactory] = []
        msgs.append(Image(announce_pic))
        if payload.url:
            msgs.append(Text(f"前往:{payload.url}"))
        return [Image(announce_pic)]
