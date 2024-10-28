import json
from json import JSONDecodeError
from typing import Literal, cast
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import httpx
from httpx import AsyncClient
from nonebot.log import logger

from ..config import config
from .http import http_client
from ..config.db_model import Cookie
from ..types import Target, RegistryMeta


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
    _site_name: str  # 绑定的 site_name，需要使用 create_cookie_client_manager 创建 Client_mgr 时绑定

    @classmethod
    async def _generate_anonymous_cookie(cls) -> Cookie:
        return Cookie(
            cookie_name=f"{cls._site_name} anonymous",
            site_name=cls._site_name,
            content="{}",
            is_universal=True,
            is_anonymous=True,
            last_usage=datetime.now(),
            cd_milliseconds=0,
            tags="{}",
            status="",
        )

    @classmethod
    async def refresh_anonymous_cookie(cls):
        """更新已有的匿名cookie，若不存在则添加"""
        existing_anonymous_cookies = await config.get_cookie(cls._site_name, is_anonymous=True)
        if existing_anonymous_cookies:
            for cookie in existing_anonymous_cookies:
                new_anonymous_cookie = await cls._generate_anonymous_cookie()
                new_anonymous_cookie.id = cookie.id  # 保持原有的id
                await config.update_cookie(new_anonymous_cookie)
        else:
            new_anonymous_cookie = await cls._generate_anonymous_cookie()
            await config.add_cookie(new_anonymous_cookie)

    @classmethod
    async def add_user_cookie(cls, content: str, cookie_name: str | None = None) -> Cookie:
        """添加用户 cookie"""
        from ..platform import site_manager

        cookie_site = cast(type[CookieSite], site_manager[cls._site_name])
        if not await cookie_site.validate_cookie(content):
            raise ValueError()
        cookie = Cookie(site_name=cls._site_name, content=content)
        cookie.cookie_name = cookie_name if cookie_name else await cookie_site.get_cookie_name(content)
        cookie.cd = cookie_site.default_cd
        cookie_id = await config.add_cookie(cookie)
        return await config.get_cookie_by_id(cookie_id)

    def _generate_hook(self, cookie: Cookie) -> callable:
        """hook 函数生成器，用于回写请求状态到数据库"""

        async def _response_hook(resp: httpx.Response):
            if resp.status_code == 200:
                logger.trace(f"请求成功: {cookie.id} {resp.request.url}")
                cookie.status = "success"
            else:
                logger.warning(f"请求失败: {cookie.id} {resp.request.url}, 状态码: {resp.status_code}")
                cookie.status = "failed"
            cookie.last_usage = datetime.now()
            await config.update_cookie(cookie)

        return _response_hook

    async def _choose_cookie(self, target: Target | None) -> Cookie:
        """选择 cookie 的具体算法"""
        cookies = await config.get_cookie(self._site_name, target)
        cookies = (cookie for cookie in cookies if cookie.last_usage + cookie.cd < datetime.now())
        cookie = min(cookies, key=lambda x: x.last_usage)
        return cookie

    async def get_client(self, target: Target | None) -> AsyncClient:
        """获取 client，根据 target 选择 cookie"""
        client = http_client()
        cookie = await self._choose_cookie(target)
        if cookie.is_universal:
            logger.trace(f"平台 {self._site_name} 未获取到用户cookie, 使用匿名cookie")
        else:
            logger.trace(f"平台 {self._site_name} 获取到用户cookie: {cookie.id}")

        return await self._assemble_client(client, cookie)

    async def _assemble_client(self, client, cookie) -> AsyncClient:
        """组装 client，可以自定义 cookie 对象的 content 装配到 client 中的方式"""
        cookies = httpx.Cookies()
        if cookie:
            cookies.update(json.loads(cookie.content))
        client.cookies = cookies
        client.event_hooks = {"response": [self._generate_hook(cookie)]}
        return client

    async def get_client_for_static(self) -> AsyncClient:
        return http_client()

    async def get_query_name_client(self) -> AsyncClient:
        return http_client()

    async def refresh_client(self):
        self.refresh_anonymous_cookie()


def is_cookie_client_manager(manger: type[ClientManager]) -> bool:
    return issubclass(manger, CookieClientManager)


def create_cookie_client_manager(site_name: str) -> type[CookieClientManager]:
    """创建一个平台特化的 CookieClientManger"""
    return type(
        "CookieClientManager",
        (CookieClientManager,),
        {"_site_name": site_name},
    )


class Site(metaclass=RegistryMeta, base=True):
    schedule_type: Literal["date", "interval", "cron"]
    schedule_setting: dict
    name: str
    client_mgr: type[ClientManager] = DefaultClientManager
    require_browser: bool = False
    registry: list[type["Site"]]

    def __str__(self):
        return f"[{self.name}]-{self.name}-{self.schedule_setting}"


class CookieSite(Site):
    client_mgr: type[CookieClientManager] = CookieClientManager
    default_cd: int = timedelta(seconds=10)

    @classmethod
    async def get_cookie_name(cls, content: str) -> str:
        """从cookie内容中获取cookie的友好名字，添加cookie时调用，持久化在数据库中"""
        from . import text_fletten

        return text_fletten(f"{cls.name} [{content[:10]}]")

    @classmethod
    async def validate_cookie(cls, content: str) -> bool:
        """验证 cookie 内容是否有效，添加 cookie 时用，可根据平台的具体情况进行重写"""
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                return False
        except JSONDecodeError:
            return False
        return True


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


class SkipRequestException(Exception):
    pass
