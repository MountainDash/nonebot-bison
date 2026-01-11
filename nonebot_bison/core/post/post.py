

from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from nonebot_bison.core.platform import PlatformConfig

from .rtf import PlainContentSupport

type Imagable = str | bytes | Path | BytesIO

@dataclass
class Post(PlainContentSupport):
    """最通用的Post，理论上包含所有常用的数据

    对于更特殊的需要，可以考虑另外实现一个Post
    """

    platform: PlatformConfig
    """来源平台"""
    content: str
    """文本内容"""
    title: str | None = None
    """标题"""
    images: Sequence[Imagable] | None = None
    """图片列表"""
    timestamp: float | None = None
    """发布/获取时间戳, 秒"""
    url: str | None = None
    """来源链接"""
    avatar: Imagable | None = None
    """发布者头像"""
    nickname: str | None = None
    """发布者昵称"""
    description: str | None = None
    """发布者个性签名等"""
    repost: "Post | None" = None
    """转发的Post"""
