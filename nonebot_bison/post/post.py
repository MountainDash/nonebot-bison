import reprlib
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from dataclasses import fields, dataclass

from nonebot.log import logger
from nonebot_plugin_saa import MessageSegmentFactory

from ..theme import theme_manager
from .abstract_post import AbstractPost
from ..plugin_config import plugin_config
from ..theme.types import ThemeRenderError, ThemeRenderUnsupportError

if TYPE_CHECKING:
    from ..platform import Platform


@dataclass
class Post(AbstractPost):
    """最通用的Post，理论上包含所有常用的数据

    对于更特殊的需要，可以考虑另外实现一个Post
    """

    platform: "Platform"
    """来源平台"""
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
    nickname: str | None = None
    """发布者昵称"""
    description: str | None = None
    """发布者个性签名等"""
    repost: "Post | None" = None
    """转发的Post"""

    def get_config_theme(self) -> str | None:
        """获取用户指定的theme"""
        return plugin_config.bison_platform_theme.get(self.platform.platform_name)

    def get_priority_themes(self) -> list[str]:
        """获取渲染所使用的theme名列表，按照优先级排序"""
        themes_by_priority: list[str] = []
        # 最先使用用户指定的theme
        if user_theme := self.get_config_theme():
            themes_by_priority.append(user_theme)
        # 然后使用平台默认的theme
        if self.platform.default_theme not in themes_by_priority:
            themes_by_priority.append(self.platform.default_theme)
        # 最后使用最基础的theme
        if "basic" not in themes_by_priority:
            themes_by_priority.append("basic")
        return themes_by_priority

    async def generate(self) -> list[MessageSegmentFactory]:
        """生成消息"""
        themes = self.get_priority_themes()
        for theme_name in themes:
            if theme := theme_manager[theme_name]:
                try:
                    logger.debug(f"Try to render Post with theme {theme_name}")
                    return await theme.do_render(self)
                except ThemeRenderUnsupportError as e:
                    logger.warning(
                        f"Theme {theme_name} does not support Post of {self.platform.__class__.__name__}: {e}"
                    )
                    continue
                except ThemeRenderError as e:
                    logger.exception(f"Theme {theme_name} render error: {e}")
                    continue
            else:
                logger.error(f"Theme {theme_name} not found")
                continue
        else:
            raise ThemeRenderError(f"No theme can render Post of {self.platform.__class__.__name__}")

    def __str__(self) -> str:
        aRepr = reprlib.Repr()
        aRepr.maxstring = 100

        post_format = f"""## Post: {id(self):X} ##

{self.content if len(self.content) < 200 else self.content[:200] + '...'}

来源: <Platform {self.platform.platform_name}>
"""
        post_format += "附加信息:\n"
        for field in fields(self):
            if field.name in ("content", "platform", "repost"):
                continue
            value = getattr(self, field.name)
            if value is not None:
                post_format += f"- {field.name}: {aRepr.repr(value)}\n"

        if self.repost:
            post_format += "\n转发:\n"
            post_format += str(self.repost)

        return post_format
