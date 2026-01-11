from abc import ABCMeta, abstractmethod
from typing import Any

from nonebot_bison.core.courier import Parcel
from nonebot_bison.core.post import Post
from nonebot_bison.utils.meta import RegistryMeta


class ThemeMeta(ABCMeta, RegistryMeta): ...


class Theme[RenderResult](metaclass=ThemeMeta, base=True):
    """theme基类"""

    name: str
    """theme名称"""

    @abstractmethod
    def is_support_register(self) -> bool:
        """检查是否允许注册该主题"""
        ...

    @abstractmethod
    async def is_support_render(self, post: Post) -> bool:
        """本主题是否支持渲染该类型的Post"""
        ...

    @abstractmethod
    async def render(self, post: Post) -> RenderResult:
        """主题的渲染结果"""
        ...

    async def package(
        self, post: Post, metadata: dict[str, Any] | None = None
    ) -> Parcel[RenderResult]:
        """将Post渲染为可供Courier发送的格式"""
        res = await self.render(post)
        inner_metadata = {
            "theme_name": self.name,
            "platform_name": post.platform.display_name,
        }
        if metadata is not None:
            metadata.update(inner_metadata)
        else:
            metadata = inner_metadata

        return Parcel(
            tag="message",
            payload=res,
            metadata=metadata,
        )


class ThemeRegistrationError(Exception):
    """Theme注册错误"""

    pass


class ThemeRenderUnsupportError(Exception):
    """Theme不支持渲染该类型的Post"""

    pass


class ThemeRenderError(Exception):
    """Theme渲染错误"""

    pass
