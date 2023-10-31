from functools import partial
from types import MappingProxyType
from collections.abc import Callable
from typing import Any, TypeVar, cast
from datetime import datetime, timedelta

from expiringdict import ExpiringDict
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

StoreType = TypeVar("StoreType")


class SimpleCache:
    """简单缓存"""

    def __init__(self, default_lifetime: timedelta = timedelta(minutes=5)):
        self.default_lifetime = default_lifetime
        self._cache: dict[str, tuple[Any, datetime, timedelta]] = {}

    def __setitem__(self, key: str, value: tuple[Any, timedelta | None]):
        value, lifetime = value
        self._cache[key] = (value, datetime.now(), lifetime or self.default_lifetime)

    def __getitem__(self, key: str):
        if item := self._cache.get(key):
            value, create_time, lifetime = item
            if datetime.now() - create_time <= lifetime:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, lifetime: timedelta | None = None):
        self[key] = (value, lifetime)

    def get(
        self, key: str, default: Any = None, value_convert_func: Callable[[Any], StoreType | None] | None = None
    ) -> StoreType | None:
        if value := self[key]:
            if value_convert_func:
                return value_convert_func(value)
            return value
        return default


class CeobeDataSourceCache:
    """数据源缓存"""

    def __init__(self):
        self._cache = ExpiringDict(max_len=100, max_age_seconds=60 * 60 * 24 * 7)
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
        cache = cast(list[CeobeTarget], self._cache.values())
        return next(filter(cond_func, cache), None)

    async def get_by_unique_id(self, unique_id: str) -> CeobeTarget | None:
        """根据unique_id获取数据源

        如果在缓存中找不到，会刷新缓存
        """
        if target := self._cache.get(unique_id):
            return cast(CeobeTarget, target)
        await self.refresh_data_sources()
        return cast(CeobeTarget | None, self._cache.get(unique_id))

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
