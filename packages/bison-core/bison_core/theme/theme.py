from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, NamedTuple
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from bison_core.post import Post

class ThemeMetadata(TypedDict, extra_items=Any):
    theme_id: str
    platform_id: str


class RenderResult[R](NamedTuple):
    """渲染结果协议"""
    result: R
    metadata: ThemeMetadata | None = None


class Theme[T](ABC):
    """theme基类"""

    name: str
    """theme名称"""

    @abstractmethod
    @classmethod
    def is_support_register(cls) -> bool:
        """检查是否允许注册该主题"""
        ...

    @abstractmethod
    async def is_support_render(self, post: Post) -> bool:
        """本主题是否支持渲染该类型的Post"""
        ...

    @abstractmethod
    async def render(self, post: Post) -> T:
        """将Post渲染为可供发送的格式，通常是字符串或图片等"""
        ...

    async def package(
        self, post: Post, metadata: dict[str, Any] | None = None
    ) -> RenderResult[T]:
        """将渲染结果进行打包，附加必要的元信息，供发送器使用"""
        res = await self.render(post)
        inner_metadata: ThemeMetadata = {
            "theme_id": self.name,
            "platform_id": post.platform.name,
        }
        inner_metadata.update(metadata or {}) #type: ignore

        return RenderResult(result=res, metadata=inner_metadata)

class ThemeRenderException(Exception):
    """Theme渲染异常"""

    theme_name: str
    post_id: str

    def __init__(self, /, theme_name: str, post_id: str, *args: Any) -> None:
        super().__init__(*args)
        self.theme_name = theme_name
        self.post_id = post_id


class ThemeRenderUnsupportError(ThemeRenderException):
    """Theme不支持渲染该类型的Post"""

    pass


class ThemeRenderError(ThemeRenderException):
    """Theme渲染错误"""

    pass
