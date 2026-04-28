from dataclasses import dataclass
import io
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, override

from pydantic import GetPydanticSchema
from pydantic_core import core_schema

from .rtf import PlainContentSupport

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bison_core.platform import PlatformConfig


def bytesio_validator(v: Any):
    if not isinstance(v, io.BytesIO):
        raise ValueError(f"Expected an instance of io.BytesIO, got {v}")
    return v


BytesIOType = Annotated[
    io.BytesIO,
    GetPydanticSchema(
        lambda tp, handler: core_schema.no_info_after_validator_function(
            function=lambda x: bytesio_validator(x), schema=core_schema.any_schema()
        )
    ),
]

type Imagable = str | bytes | Path | BytesIOType


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
    extras: dict[str, Any] | None = None
    """其他非标准数据"""

    @override
    async def get_plain_content(self) -> str:
        return self.content
