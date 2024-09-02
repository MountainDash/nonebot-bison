import json
from typing import Literal
from abc import ABC, abstractmethod

import httpx
from httpx import AsyncClient

from ..types import Target
from ..config import config
from .http import http_client


class ClientManager(ABC):
    @abstractmethod
    async def get_client(self, target: Target | None) -> AsyncClient: ...

    @abstractmethod
    async def get_client_for_static(self) -> AsyncClient: ...

    @abstractmethod
    async def get_query_name_client(self) -> AsyncClient: ...

    @abstractmethod
    async def refresh_client(self): ...


class DefaultClientManager(ClientManager):
    async def get_client(self, target: Target | None) -> AsyncClient:
        return http_client()

    async def get_client_for_static(self) -> AsyncClient:
        return http_client()

    async def get_query_name_client(self) -> AsyncClient:
        return http_client()

    async def refresh_client(self):
        pass


class CookieClientManager(ClientManager):
    _platform_name: str

    async def _choose_cookie(self, target: Target) -> dict[str, str]:
        if not target:
            return {}
        cookies = await config.get_cookie_by_target(target, self._platform_name)
        if not cookies:
            return {}
        cookie = sorted(cookies, key=lambda x: x.last_usage, reverse=True)[0]
        return json.loads(cookie.content)

    async def get_client(self, target: Target | None) -> AsyncClient:
        client = http_client()
        cookie = await self._choose_cookie(target)
        cookies = httpx.Cookies()
        if cookie:
            cookies.update(cookie)
        client.cookies = cookies
        return client

    async def get_client_for_static(self) -> AsyncClient:
        pass

    async def get_query_name_client(self) -> AsyncClient:
        pass

    async def refresh_client(self):
        pass


def create_cookie_client_manager(platform_name: str) -> type[CookieClientManager]:
    return type(
        "CookieClientManager",
        (CookieClientManager,),
        {"_platform_name": platform_name},
    )


class Site:
    schedule_type: Literal["date", "interval", "cron"]
    schedule_setting: dict
    name: str
    client_mgr: type[ClientManager] = DefaultClientManager
    require_browser: bool = False

    def __str__(self):
        return f"[{self.name}]-{self.name}-{self.schedule_setting}"


def anonymous_site(schedule_type: Literal["date", "interval", "cron"], schedule_setting: dict) -> type[Site]:
    return type(
        "AnonymousSite",
        (Site,),
        {
            "schedule_type": schedule_type,
            "schedule_setting": schedule_setting,
            "client_mgr": DefaultClientManager,
        },
    )
