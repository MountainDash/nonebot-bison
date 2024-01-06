from io import BytesIO
from typing import Any
from pathlib import Path
from dataclasses import field, dataclass

from httpx import AsyncClient
from nonebot_plugin_saa import MessageFactory


@dataclass
class PostHeader:
    """Post的头部信息, 是不会被渲染的部分"""

    platform_code: str
    """本 Post 来源 Platform 在 platform_manager 中的 code, 用于获取 Platform 实例, 一般来说是 platform.platform_name"""
    # TODO：要不规范一下 Platform那边 platform_name 和 name 的命名？
    http_client: AsyncClient
    """本 Post 使用的 http_client, 用于获取图片等资源, 一般来说是 platform.client"""
    recommend_theme: str
    """Platform 推荐使用的 theme, 一般来说是 platfofm.default_theme"""
    compress: bool = False
    """是否将 Post 压缩为一条消息"""


@dataclass
class PostPayload:
    """Post的内容信息, 是会被渲染的部分"""

    content: str
    """文本内容"""
    title: str | None = None
    """标题"""
    images: list[str | bytes | Path | BytesIO] | None = None
    """图片列表"""
    timestamp: int | None = None
    """发布/获取时间戳"""
    url: str | None = None
    """来源链接"""
    avatar: str | bytes | Path | BytesIO | None = None
    """发布者头像"""
    author: str | None = None
    """发布者名称"""
    description: str | None = None
    """发布者个性签名等"""
    platform: str | None = None
    """来源平台名称, 一般为 Platform.name"""
    repost: "Post | None" = None
    """转发的Post"""


@dataclass
class PostExtra:
    """Post的额外信息, 是不会被渲染的部分"""

    messsage: list[MessageFactory] | None = None
    """额外的消息, 一般用于发送附加消息"""
    others: dict[str, Any] | None = None
    """其他信息, 一般用于存储一些额外信息"""


@dataclass
class Post:
    header: PostHeader
    payload: PostPayload
    extra: PostExtra = field(default_factory=PostExtra)
