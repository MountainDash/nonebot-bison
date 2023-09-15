from pathlib import Path

from nonebot import require
from nonebot_plugin_saa import Image

from ...types import BaseStem

HTML = str
CARD_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "announce.html.jinja"


class Stem(BaseStem):
    """Arknight 公告卡片

    announce_title: 公告标题
    banner_image_url: 横幅图片 URL
    content: 公告内容, 应为 HTML 文本
    """

    announce_title: str
    banner_image_url: str | None
    content: HTML

    @classmethod
    def get_theme_name(cls):
        return "arknights"

    async def render(self) -> Image:
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import template_to_pic

        return Image(
            await template_to_pic(
                template_path=CARD_DIR.as_posix(),
                template_name=TEMPLATE_NAME,
                templates={
                    "card": self,
                    "base_url": f"file://{CARD_DIR}",
                },
                pages={
                    "viewport": {"width": 600, "height": 100},
                    "base_url": CARD_DIR,
                },
            )
        )
