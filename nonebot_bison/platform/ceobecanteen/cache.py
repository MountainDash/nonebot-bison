from collections.abc import Callable
from datetime import timedelta
from functools import partial
from types import MappingProxyType
from typing import TypeAlias

from expiringdictx import ExpiringDict, SimpleCache
from hishel import AsyncCacheTransport, AsyncInMemoryStorage, Controller
from httpx import AsyncClient, AsyncHTTPTransport

from .const import DATASOURCE_URL
from .models import CeobeSource, CeobeTarget, DataSourceResponse
from .utils import process_response

cache_transport = AsyncCacheTransport(
    AsyncHTTPTransport(),
    storage=AsyncInMemoryStorage(),
    controller=Controller(
        always_revalidate=True,
    ),
)

CeobeClient = partial(
    AsyncClient,
    transport=cache_transport,
)

UniqueId: TypeAlias = str


class CeobeCache:
    # 不在 __init__ 中初始化，让多个实例共享一个缓存
    _cache = SimpleCache()

    def __init__(self, lifetime: timedelta, store_key: str | None = None):
        self.store_key = store_key
        self.lifetime = lifetime

    def __set_name__(self, owner, name: str):
        self.key = self.store_key or name

    def __get__(self, instance, owner):
        return self._cache.get(self.key)

    def __set__(self, instance, value):
        self._cache[self.key, self.lifetime] = value


class CeobeDataSourceCache:
    """数据源缓存, 以unique_id为key存储数据源"""

    def __init__(self):
        self._cache = ExpiringDict[UniqueId, CeobeTarget](capacity=100, default_age=timedelta(days=1))
        self.client = CeobeClient()
        self.url = DATASOURCE_URL

    @property
    def cache(self) -> MappingProxyType[str, CeobeTarget]:
        return MappingProxyType(self._cache)

    async def refresh_data_sources(self) -> MappingProxyType[UniqueId, CeobeTarget]:
        """请求数据源API刷新缓存"""
        data_sources_resp = await self.client.get(self.url)
        data_sources = process_response(data_sources_resp, DataSourceResponse).data
        for ds in data_sources:
            self._cache[ds.unique_id] = ds
        return self.cache

    async def get_all(self, force_refresh: bool = False) -> MappingProxyType[UniqueId, CeobeTarget]:
        """获取所有数据源, 如果缓存为空则尝试刷新缓存"""
        if not self.cache or force_refresh:
            await self.refresh_data_sources()
        return self.cache

    def select_one(self, cond_func: Callable[[CeobeTarget], bool]) -> CeobeTarget | None:
        """根据条件获取数据源

        不会刷新缓存
        """
        cache = self._cache.values()
        return next(filter(cond_func, cache), None)

    async def get_by_unique_id(self, unique_id: str) -> CeobeTarget | None:
        """根据unique_id获取数据源

        如果在缓存中找不到，会刷新缓存
        """
        if target := self._cache.get(unique_id):
            return target
        await self.refresh_data_sources()
        return self._cache.get(unique_id)

    async def get_by_nickname(self, nickname: str) -> CeobeTarget | None:
        """根据nickname获取数据源

        如果在缓存中找不到，会刷新缓存
        """

        def select_by_nickname(target: CeobeTarget):
            return target.nickname == nickname

        if target := self.select_one(select_by_nickname):
            return target
        await self.refresh_data_sources()
        return self.select_one(select_by_nickname)

    async def get_by_source(self, source: CeobeSource) -> CeobeTarget | None:
        """根据source获取数据源

        如果在缓存中找不到，会刷新缓存
        """

        def select_by_source(target: CeobeTarget):
            return target.db_unique_key == source.data and target.datasource == source.type

        if target := self.select_one(select_by_source):
            return target
        await self.refresh_data_sources()
        return self.select_one(select_by_source)
