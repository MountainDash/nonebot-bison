from typing import Literal, Optional, Union

from nonebot.log import logger
from pydantic import BaseModel, validator

from .utils import _check_text_overflow, _cut_text_with_half_width

# colorful card 支持的类型
# common: 普通的卡片 只有头像，名称，发布时间和纯文字内容
# video: 视频卡片 在common的基础上增加了视频封面，标题，简介
# repost: 转发卡片 在common的基础上增加了转发的原内容显示
# 具体可以参考B站的卡片样式
# 可选类型应与需要使用的模板文件名一致
SupportedCard = Literal["common", "video", "live", "repost"]
SupportedContent = Union[
    "CommonContent", "VideoContent", "LiveContent", "RepostContent"
]

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
        return _check_text_overflow(
            v, max_half_width, max_half_width_per_line, max_line
        )

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
        if v.type == "repost" or isinstance(v.content, RepostContent):
            raise TypeError("nested repost is not allowed")
        return v


class Card(BaseModel):
    type: SupportedCard
    header: CardHeader
    content: SupportedContent
    # 可以在html模板文件<head>内自行添加的内容，包括但不限于css和js
    extra_head: Optional[str] = None

    class Config:
        # https://docs.pydantic.dev/latest/usage/model_config/#smart-union
        smart_union = True

    # 确保内容与类型匹配，且不能为嵌套转发
    @validator("content")
    def check_content(cls, v: SupportedContent, values):
        if values["type"] == "common" and not isinstance(v, CommonContent):
            raise TypeError("content type is not match")
        if values["type"] == "video" and not isinstance(v, VideoContent):
            raise TypeError("content type is not match")
        if values["type"] == "live" and not isinstance(v, LiveContent):
            raise TypeError("content type is not match")
        if values["type"] == "repost" and not isinstance(v, RepostContent):
            raise TypeError("content type is not match")
        return v


# https://docs.pydantic.dev/latest/usage/postponed_annotations/
RepostContent.update_forward_refs()
