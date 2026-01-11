from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Iterable
from typing import Self

from nonebot_plugin_saa import PlatformTarget

from nonebot_bison.core.post import Post
from nonebot_bison.core.schedule import SubUnit
from nonebot_bison.core.site import ProcessContext, SiteConfig
from nonebot_bison.utils.classproperty import classproperty
from nonebot_bison.utils.meta import RegistryMeta

from .config import PlatformConfig

type TargetedPosts = list[
    tuple[PlatformTarget, list[Post]]
]


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
    @abstractmethod
    async def fetch(self, sub_unit: SubUnit) -> TargetedPosts:
        """获取指定订阅单元的最新消息"""
        ...


class BatchFetchMixin(ABC):
    @abstractmethod
    async def fetch(self, sub_units: Iterable[SubUnit]) -> TargetedPosts:
        """批量获取指定订阅单元的最新消息"""
        ...


# 订阅行为混入类
class FilterMixin[RawPost](ABC):
    @abstractmethod
    async def filter(self, raw_posts: Iterable[RawPost]) -> tuple[RawPost, ...]:
        """过滤消息, 返回符合订阅条件的消息"""
        ...
