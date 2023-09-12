from pathlib import Path

import jinja2
from nonebot import require
from nonebot_plugin_saa import Image
from pydantic import BaseModel, validator, root_validator

from ...types import BaseStem
from ...utils import convert_to_qr

card_dir = Path(__file__).parent / "templates"
TEMPLATE_NAME = "ceobecanteen.html.jinja"


class CeoboInfo(BaseModel):
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


class Card(BaseStem):
    """卡片

    info: 卡片的信息部分
    content: 卡片的内容部分
    qr: 二维码链接
    """

    info: CeoboInfo
    content: CeoboContent
    qr: str

    @validator("qr")
    def convert_qr(cls, v):
        if not v.startswith("http"):
            raise ValueError("qr must be a valid url")
        return convert_to_qr(v)

    async def render(self) -> Image:
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import get_new_page

        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(card_dir),
            enable_async=True,
        )
        template = template_env.get_template(TEMPLATE_NAME)
        html = await template.render_async(card=self)
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
        return Image(img_raw)
