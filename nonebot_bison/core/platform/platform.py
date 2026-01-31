from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Self

from nonebot_plugin_saa import PlatformTarget

from nonebot_bison.core.post import Post
from nonebot_bison.core.schedule import SubUnit
from nonebot_bison.core.site import ProcessContext, SiteConfig
from nonebot_bison.typing import Category, Tag, Target
from nonebot_bison.utils.classproperty import classproperty
from nonebot_bison.utils.meta import RegistryMeta

from .config import PlatformConfig

type TargetedPosts = list[tuple[PlatformTarget, list[Post]]]


class CategoryException(Exception):
    """base class for category related exceptions"""


class CategoryNotSupported(CategoryException):
    """raise in get_category, when you know the category of the post
    but don't want to support it or don't support its parsing yet
    """


class CategoryNotRecognize(CategoryException):
    """raise in get_category, when you don't know the category of post"""


class PlatformMeta(ABCMeta, RegistryMeta): ...


# 基本平台
class Platform[RawPost](metaclass=PlatformMeta, base=True):

    site_config: SiteConfig
    """平台所属站点配置"""
    platform_config: PlatformConfig
    """平台配置"""
    ctx: ProcessContext
    """平台运行时上下文, 运行时注入"""

    @classproperty
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """平台名称"""
        ...

    @classmethod
    def bound(cls, ctx: ProcessContext) -> Self:
        """绑定运行时上下文"""
        p = cls()
        p.ctx = ctx
        return p

    @abstractmethod
    def parse(self, raw_post: RawPost) -> Post:
        """解析原始消息为统一消息报文"""
        ...


# 获取行为混入类
class FetchMixin(ABC):
    if TYPE_CHECKING:
        ctx: ProcessContext

    @abstractmethod
    async def fetch(self, sub_unit: SubUnit) -> TargetedPosts:
        """获取指定订阅单元的最新消息"""
        ...


class BatchFetchMixin(ABC):
    if TYPE_CHECKING:
        ctx: ProcessContext

    @abstractmethod
    async def fetch(self, sub_units: Iterable[SubUnit]) -> TargetedPosts:
        """批量获取指定订阅单元的最新消息"""
        ...


# 订阅行为混入类
class FilterMixin[RawPost](ABC):
    if TYPE_CHECKING:
        platform_config: PlatformConfig
        """平台配置"""
        ctx: ProcessContext
        """平台运行时上下文, 运行时注入"""

        @classproperty
        @classmethod
        @abstractmethod
        def name(cls) -> str:
            """平台名称"""
            ...

    @abstractmethod
    def get_category(self, raw_post: RawPost) -> Category | None: ...

    @abstractmethod
    def get_tags(self, raw_post: RawPost) -> set[str]: ...

    @abstractmethod
    async def filter(
        self, target: Target, raw_posts: Iterable[RawPost]
    ) -> tuple[RawPost, ...]:
        """过滤消息, 返回符合订阅条件的消息"""
        ...

    def _is_banned_post(
        self,
        post_tags: Iterable[Tag],
        subscribed_tags: Iterable[Tag],
        banned_tags: Iterable[Tag],
    ) -> bool:
        """只要存在任意屏蔽tag则返回真，此行为优先级最高。
        存在任意被订阅tag则返回假，此行为优先级次之。
        若被订阅tag为空，则返回假。
        """
        # 存在任意需要屏蔽的tag则为真
        if banned_tags:
            for tag in post_tags or []:
                if tag in banned_tags:
                    return True
        # 检测屏蔽tag后，再检测订阅tag
        # 存在任意需要订阅的tag则为假
        if subscribed_tags:
            ban_it = True
            for tag in post_tags or []:
                if tag in subscribed_tags:
                    ban_it = False
            return ban_it
        else:
            return False

    def _tag_separator(self, stored_tags: Iterable[Tag]) -> tuple[list[Tag], list[Tag]]:
        """返回分离好的正反tag元组"""
        subscribed_tags = []
        banned_tags = []
        for tag in stored_tags:
            if tag.startswith("~"):
                banned_tags.append(tag.lstrip("~"))
            else:
                subscribed_tags.append(tag)
        return subscribed_tags, banned_tags

    async def subscriber_filter(
        self,
        raw_posts: Iterable[RawPost],
        needed_cats: Iterable[Category],
        required_tags: Iterable[Tag],
    ) -> tuple[RawPost, ...]:
        """过滤出符合订阅用户要求的报文"""
        res: list[RawPost] = []
        for raw_post in raw_posts:
            if self.platform_config.categories:
                if (cat := self.get_category(raw_post)) and cat not in needed_cats:
                    continue
            if self.platform_config.enable_tag and required_tags:
                tags = self.get_tags(raw_post)
                if self._is_banned_post(tags, *self._tag_separator(tags)):
                    continue
            res.append(raw_post)

        return tuple(res)
