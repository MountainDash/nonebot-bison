from functools import partial
from datetime import timedelta
from types import MappingProxyType
from collections.abc import Callable

from expiringdictx import ExpiringDict
from hishel import Controller, AsyncCacheClient, AsyncFileStorage

from .const import DATASOURCE_URL
from .utils import process_response
from .models import CeobeSource, CeobeTarget, DataSourceResponse

CeobeClient = partial(
    AsyncCacheClient,
    headers={"Bot": "Nonebot-Bison", "Cache-Control": "max-age=0"},
    controller=Controller(),
    storage=AsyncFileStorage(ttl=300),
)


class CeobeDataSourceCache:
    """数据源缓存"""

    def __init__(self):
        self._cache = ExpiringDict[str, CeobeTarget](capacity=100, default_age=timedelta(days=7))
        self.client = CeobeClient()
        self.url = DATASOURCE_URL
        self.init_requested = False

    @property
    def cache(self) -> MappingProxyType[str, CeobeTarget]:
        return MappingProxyType(self._cache)

    async def refresh_data_sources(self):
        """请求数据源API刷新缓存"""
        data_sources_resp = await self.client.get(self.url)
        data_sources = process_response(data_sources_resp, DataSourceResponse).data
        for ds in data_sources:
            self._cache[ds.unique_id] = ds
        return self.cache

    async def get_all(self):
        if not self.init_requested:
            await self.refresh_data_sources()
            self.init_requested = True
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

        def cond_func(target: CeobeTarget):
            return target.nickname == nickname

        if target := self.select_one(cond_func):
            return target
        await self.refresh_data_sources()
        return self.select_one(cond_func)

    async def get_by_source(self, source: CeobeSource) -> CeobeTarget | None:
        """根据source获取数据源

        如果在缓存中找不到，会刷新缓存
        """

        def cond_func(target: CeobeTarget):
            return target.db_unique_key == source.data and target.datasource == source.type

        if target := self.select_one(cond_func):
            return target
        await self.refresh_data_sources()
        return self.select_one(cond_func)
