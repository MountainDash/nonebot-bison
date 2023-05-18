from pathlib import Path

from nonebot import require
from nonebot.adapters.onebot.v11.message import MessageSegment

from .types import Card

card_dir = Path(__file__).parent / "templates" / "card"


async def card_render(card: Card) -> MessageSegment:
    """将Card类提供的数据导入jinja模板渲染, 并返回图片消息段"""
    require("nonebot_plugin_htmlrender")
    from nonebot_plugin_htmlrender import template_to_pic as _template_to_pic

    template_name = f"{card.type}.html"

    card_pic = await _template_to_pic(
        template_path=card_dir.as_posix(),
        template_name=template_name,
        templates={"card": card},
        pages={
            "viewport": {"width": 1000, "height": 3000},
            "base_url": card_dir.as_uri(),
        },
        wait=1,
    )

    return MessageSegment.image(card_pic)
