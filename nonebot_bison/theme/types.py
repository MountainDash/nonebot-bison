from typing import TYPE_CHECKING
from abc import ABC, abstractmethod

from pydantic import BaseModel
from nonebot_plugin_saa import MessageSegmentFactory

if TYPE_CHECKING:
    from ..post.abstract_post import AbstractPost


class AbstractTheme(ABC, BaseModel):
    """theme基类"""

    name: str
    """theme名称"""

    @abstractmethod
    async def render(self, post: "AbstractPost") -> list[MessageSegmentFactory]:
        """对多个Post的实例可以考虑使用@overload"""
        ...


class ThemeRegistrationError(Exception):
    """Theme注册错误"""

    pass


class ThemeRenderUnsupportError(Exception):
    """Theme不支持渲染该类型的Post"""

    pass


class ThemeRenderError(Exception):
    """Theme渲染错误"""

    pass
