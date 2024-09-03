import json
from typing import Literal
from abc import ABC, abstractmethod

import httpx
from httpx import AsyncClient
from nonebot.log import logger

from ..types import Target
from ..config import config
from .http import http_client
from ..config.db_model import Cookie


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

    def _generate_hook(self, cookie: Cookie):
        async def _response_hook(resp: httpx.Response):
            if not cookie:
                logger.debug(f"未携带bison cookie: {resp.request.url}")
            if resp.status_code == 200:
                logger.debug(f"请求成功: {cookie.id} {resp.request.url}")

            else:
                logger.error(f"请求失败:{cookie.id} {resp.request.url}, 状态码: {resp.status_code}")

        return _response_hook

    async def _choose_cookie(self, target: Target) -> Cookie:
        if not target:
            return Cookie(content="{}")
        cookies = await config.get_cookie_by_target(target, self._platform_name)
        if not cookies:
            return Cookie(content="{}")
        cookie = sorted(cookies, key=lambda x: x.last_usage, reverse=True)[0]
        return cookie

    async def get_client(self, target: Target | None) -> AsyncClient:
        client = http_client()
        cookie = await self._choose_cookie(target)
        if cookie.content != "{}":
            logger.debug(f"平台 {self._platform_name} 获取到用户cookie: {cookie.id}")
        else:
            logger.debug(f"平台 {self._platform_name} 未获取到用户cookie, 使用空cookie")

        cookies = httpx.Cookies()
        if cookie:
            cookies.update(json.loads(cookie.content))
        client.cookies = cookies
        client._bison_cookie = cookie
        client.event_hooks = {"response": [self._generate_hook(cookie)]}
        return client

    async def get_client_for_static(self) -> AsyncClient:
        return http_client()

    async def get_query_name_client(self) -> AsyncClient:
        return http_client()

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
