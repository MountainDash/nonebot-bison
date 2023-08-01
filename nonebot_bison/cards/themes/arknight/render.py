from pathlib import Path

from nonebot import require

from .schemas import Card

card_dir = Path(__file__).parent / "templates"
TEMPLATE_NAME = "announce.html.jinja"


async def card_render(card: Card) -> bytes:
    require("nonebot_plugin_htmlrender")
    from nonebot_plugin_htmlrender import template_to_pic

    return await template_to_pic(
        template_path=card_dir.as_uri(),
        template_name=TEMPLATE_NAME,
        templates={
            "card": card,
            "base_url": f"file://{card_dir}",
        },
        pages={
            "viewport": {"width": 500, "height": 6400},
            "base_url": card_dir.as_uri(),
        },
    )
