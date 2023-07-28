from pathlib import Path

import jinja2
from nonebot import require

from .schemas import Card

card_dir = Path(__file__).parent / "templates"
TEMPLATE_NAME = "ceobecanteen.html.jinja"


async def card_render(card: Card) -> bytes:
    require("nonebot_plugin_htmlrender")
    from nonebot_plugin_htmlrender import get_new_page

    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(card_dir),
        enable_async=True,
    )
    template = template_env.get_template(TEMPLATE_NAME)
    html = await template.render_async(card=card)
    pages = {
        "viewport": {"width": 1000, "height": 3000},
        "base_url": card_dir.as_uri(),
    }
    async with get_new_page(**pages) as page:
        await page.goto(card_dir.as_uri())
        await page.set_content(html)
        await page.wait_for_timeout(1)
        img_raw = await page.locator("#ceobecanteen-card").screenshot(
            type="png",
        )
    return img_raw
