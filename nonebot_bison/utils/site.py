import json
from typing import Literal
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

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


def is_cookie_client_manager(manger: type[ClientManager]) -> bool:
    return hasattr(manger, "_cookie_client_manger_")


class CookieClientManager(ClientManager):
    _cookie_client_manger_ = True
    _platform_name: str
    _cookie_cd: int = 10

    def _generate_hook(self, cookie: Cookie):
        """hook函数生成器，用于回写请求状态到数据库"""

        async def _response_hook(resp: httpx.Response):
            if resp.status_code == 200:
                logger.debug(f"请求成功: {cookie.id} {resp.request.url}")
                cookie.status = "success"
            else:
                logger.error(f"请求失败:{cookie.id} {resp.request.url}, 状态码: {resp.status_code}")
                cookie.status = "failed"
            cookie.last_usage = datetime.now()
            await config.update_cookie(cookie)

        return _response_hook

    @classmethod
    async def init_universal_cookie(cls):
        """移除已有的匿名cookie，添加一个新的匿名cookie"""
        universal_cookies = await config.get_unviersal_cookie(cls._platform_name)
        for cookie in universal_cookies:
            await config.delete_cookie(cookie.id)
        universal_cookie = Cookie(platform_name=cls._platform_name, content="{}", is_universal=True)
        await config.add_cookie(universal_cookie)

    @classmethod
    async def init_cookie(cls, cookie: Cookie):
        """初始化cookie，添加用户cookie时使用"""
        cookie.cd = cls._cookie_cd

    async def _choose_cookie(self, target: Target) -> Cookie:
        """选择 cookie 的具体算法"""
        if not target:
            return Cookie(content="{}")
        cookies = [
            *(await config.get_cookie_by_target(target, self._platform_name)),
            *(await config.get_universal_cookie(self._platform_name)),
        ]
        cookies = (cookie for cookie in cookies if cookie.last_usage + timedelta(seconds=cookie.cd) < datetime.now())
        cookie = min(cookies, key=lambda x: x.last_usage)
        return cookie

    async def _check_cookie(self, cookie: Cookie) -> Cookie:
        """检查Cookie，可以做一些自定义的逻辑，比如说Site的统一风控"""
        return cookie

    async def get_client(self, target: Target | None) -> AsyncClient:
        """获取 client，根据 target 选择 cookie"""
        client = http_client()
        cookie = await self._choose_cookie(target)
        if cookie.is_universal:
            logger.debug(f"平台 {self._platform_name} 未获取到用户cookie, 使用匿名cookie")
        else:
            logger.debug(f"平台 {self._platform_name} 获取到用户cookie: {cookie.id}")

        return await self._assemble_client(client, cookie)

    async def _assemble_client(self, client, cookie):
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
    """创建一个平台特化的 CookieClientManger"""
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
