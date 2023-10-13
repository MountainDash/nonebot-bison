from typing import TYPE_CHECKING
from abc import ABC, abstractmethod

from nonebot import logger, require
from pydantic import BaseModel, PrivateAttr
from nonebot_plugin_saa import MessageSegmentFactory

from ..plugin_config import plugin_config

if TYPE_CHECKING:
    from ..post.abstract_post import AbstractPost


class Theme(ABC, BaseModel):
    """theme基类"""

    name: str
    """theme名称"""
    need_browser: bool = False
    """是否需要使用浏览器"""

    _browser_checked: bool = PrivateAttr(default=False)

    async def is_support_render(self, post: "AbstractPost") -> bool:
        """是否支持渲染该类型的Post"""
        if self.need_browser and not plugin_config.bison_theme_use_browser:
            logger.warning(f"Theme {self.name} need browser, but `bison_theme_use_browser` is False")
            return False
        return True

    async def prepare(self):
        if self.need_browser:
            self.check_htmlrender_plugin_enable()

    async def do_render(self, post: "AbstractPost") -> list[MessageSegmentFactory]:
        """真正调用的渲染函数，会对渲染过程进行一些处理"""
        if not await self.is_support_render(post):
            raise ThemeRenderUnsupportError(f"Theme [{self.name}] does not support render {post} by support check")

        await self.prepare()

        return await self.render(post)

    def check_htmlrender_plugin_enable(self):
        """根据`need_browser`检测渲染插件"""
        if self._browser_checked:
            return
        try:
            require("nonebot_plugin_htmlrender")
            self._browser_checked = True
        except RuntimeError as e:
            if "Cannot load plugin" in str(e):
                raise ThemeRenderUnsupportError("需要安装`nonebot_plugin_htmlrender`插件")
            else:
                raise e

    @abstractmethod
    async def render(self, post: "AbstractPost") -> list[MessageSegmentFactory]:
        """对多种Post的实例可以考虑使用@overload"""
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
