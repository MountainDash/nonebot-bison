from pathlib import Path
from typing import Union

import jinja2
from nonebot import require
from nonebot_plugin_saa import Image
from pydantic import BaseModel, validator

from ...types import BaseStem
from .utils import _check_text_overflow, _cut_text_with_half_width

# Bison Card 支持的类型
# common: 普通的卡片 只有头像，名称，发布时间和纯文字内容
# video: 视频卡片 在common的基础上增加了视频封面，标题，简介
# repost: 转发卡片 在common的基础上增加了转发的原内容显示
# 具体可以参考B站的卡片样式

CARD_DIR = Path(__file__).parent / "templates"

SupportedContent = Union["CommonContent", "VideoContent", "LiveContent", "RepostContent"]

NAME_MAP = {
    "CommonContent": "live",
    "VideoContent": "video",
    "LiveContent": "live",
    "RepostContent": "repost",
}

# 简介最多3行，每行20全角字符，每个全角字符占2个半角字符
max_half_width = 3 * 20 * 2
max_line = 3
max_half_width_per_line = 20 * 2


class CardHeader(BaseModel):
    face: str  # 头像链接
    name: str  # 名称
    desc: str  # 发布时间/推送类型等
    platform: str  # 平台名称


class CommonContent(BaseModel):
    text: str  # 文字内容

    @validator("text")
    def newline_to_br(cls, v: str):
        return v.replace("\n", "<br>")


class VideoContent(BaseModel):
    text: str  # 文字内容
    cover: str  # 封面图片链接
    title: str  # 视频标题
    brief: str  # 视频简介
    category: str  # 视频分类/分区/标签

    @validator("brief")
    def shorten_brief(cls, v: str):
        # validator顺序是从上到下的，所以这里先检查是否会超出css盒子
        return _check_text_overflow(v, max_half_width, max_half_width_per_line, max_line)

    @validator("text", "brief")
    def newline_to_br(cls, v: str):
        return v.replace("\n", "<br>")

    @validator("title")
    def shorten_title(cls, v: str):
        return _cut_text_with_half_width(v, max_half_width_per_line - 2)


class LiveContent(BaseModel):
    text: str  # 文字内容
    cover: str  # 大图链接

    @validator("text")
    def newline_to_br(cls, v: str):
        return v.replace("\n", "<br>")


class RepostContent(BaseModel):
    text: str  # 文字内容
    repost: "Card"  # 转发的内容

    @validator("text")
    def newline_to_br(cls, v: str):
        return v.replace("\n", "<br>")

    # 不允许转发里还是转发
    @validator("repost")
    def deny_nested_repost(cls, v: "Card"):
        if type(v.content) == RepostContent:
            raise TypeError("nested repost is not allowed")


class Card(BaseStem):
    header: CardHeader
    content: SupportedContent
    # 可以在html模板文件<head>内自行添加的内容，包括但不限于css和js
    extra_head: str | None = None

    class Config:
        # 因为content的类型是Union，pydantic在默认情况下只会认为是其中的第一种类型
        # 因此需要开启smart_union来让pydantic准确判断类型
        # 参见：https://docs.pydantic.dev/latest/usage/model_config/#smart-union
        smart_union = True

    @property
    def type(self):
        return NAME_MAP[type(self.content).__name__]

    async def render(self) -> Image:
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import get_new_page

        template_name = f"{Card.type}.html.jinja"

        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(CARD_DIR),
            enable_async=True,
        )
        template = template_env.get_template(template_name)
        html = await template.render_async(card=self)
        pages = {
            "viewport": {"width": 1000, "height": 3000},
            "base_url": CARD_DIR.as_uri(),
        }
        async with get_new_page(**pages) as page:
            await page.goto(CARD_DIR.as_uri())
            await page.set_content(html)
            await page.wait_for_timeout(1)
            img_raw = await page.locator("#display").screenshot(
                type="png",
            )
        return Image(img_raw)


# RepostContent中的Card在其自身被定义之前，因此需要使用update_forward_refs来完成类型的定义
# 参见: https://docs.pydantic.dev/latest/usage/postponed_annotations/
RepostContent.update_forward_refs()
