from pathlib import Path

from nonebot import require

from .schemas import Card

CARD_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "announce.html.jinja"


async def card_render(card: Card) -> bytes:
    require("nonebot_plugin_htmlrender")
    from nonebot_plugin_htmlrender import template_to_pic

    return await template_to_pic(
        template_path=CARD_DIR.as_posix(),
        template_name=TEMPLATE_NAME,
        templates={
            "card": card,
            "base_url": f"file://{CARD_DIR}",
        },
        pages={
            "viewport": {"width": 500, "height": 100},
            "base_url": CARD_DIR,
        },
    )
