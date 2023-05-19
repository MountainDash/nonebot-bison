from pathlib import Path

from nonebot import require
from nonebot.adapters.onebot.v11.message import MessageSegment

from .types import Card

card_dir = Path(__file__).parent / "templates" / "card"


async def card_template_to_pic(template_name: str, card: Card) -> bytes:
    require("nonebot_plugin_htmlrender")
    import jinja2
    from nonebot_plugin_htmlrender import get_new_page

    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(card_dir),
        enable_async=True,
    )
    template = template_env.get_template(template_name)
    html = await template.render_async(card=card)
    pages = {
        "viewport": {"width": 1000, "height": 3000},
        "base_url": card_dir.as_uri(),
    }
    async with get_new_page(**pages) as page:
        await page.goto(card_dir.as_uri())
        await page.set_content(html)
        await page.wait_for_timeout(1)
        img_raw = await page.locator("#show").screenshot(
            type="png",
        )
    return img_raw


async def card_render(card: Card) -> MessageSegment:
    """将Card类提供的数据导入jinja模板渲染, 并返回图片消息段"""
    template_name = f"{card.type}.html"

    card_pic = await card_template_to_pic(template_name, card)

    return MessageSegment.image(card_pic)
