from typing import Literal, Union

from pydantic import BaseModel, validator

# colorful card 支持的类型
# common: 普通的卡片 只有头像，名称，发布时间和纯文字内容
# video: 视频卡片 在common的基础上增加了视频封面，标题，简介
# repost: 转发卡片 在common的基础上增加了转发的原内容显示
# 具体可以参考B站的卡片样式
# 可选类型应与需要使用的模板文件名一致
SupportedCard = Literal["common", "video", "repost"]
SupportedContent = Union["CommonContent", "VideoContent", "RepostContent"]


class CardHeader(BaseModel):
    face: str  # 头像链接
    name: str  # 名称
    desc: str  # 发布时间/推送类型等
    platform: str  # 平台名称


class CommonContent(BaseModel):
    text: str  # 文字内容


class VideoContent(BaseModel):
    text: str  # 文字内容
    cover: str  # 封面图片链接
    title: str  # 视频标题
    brief: str  # 视频简介
    category: str  # 视频分类/分区/标签


class RepostContent(BaseModel):
    text: str  # 文字内容
    repost: "Card"  # 转发的内容

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
        if values["type"] == "repost" and not isinstance(v, RepostContent):
            raise TypeError("content type is not match")
        return v


# https://docs.pydantic.dev/latest/usage/postponed_annotations/
RepostContent.update_forward_refs()
