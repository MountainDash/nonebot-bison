import json
from typing import Literal
from json import JSONDecodeError
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
    _site_name: str
    _default_cd: int = timedelta(seconds=10)

    @classmethod
    async def refresh_anonymous_cookie(cls):
        """移除已有的匿名cookie，添加一个新的匿名cookie"""
        anonymous_cookies = await config.get_cookie(cls._site_name, is_anonymous=True)
        anonymous_cookie = Cookie(site_name=cls._site_name, content="{}", is_universal=True, is_anonymous=True)
        for cookie in anonymous_cookies:
            if not cookie.is_anonymous:
                continue
            await config.delete_cookie_by_id(cookie.id)
            anonymous_cookie.id = cookie.id  # 保持原有的id
        anonymous_cookie.last_usage = datetime.now()  # 使得第一次请求优先使用用户 cookie
        await config.add_cookie(anonymous_cookie)

    @classmethod
    async def add_user_cookie(cls, content: str):
        """添加用户 cookie"""
        cookie = Cookie(site_name=cls._site_name, content=content)
        cookie.cd = cls._default_cd
        await config.add_cookie(cookie)

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

    @classmethod
    async def get_cookie_friendly_name(cls, cookie: Cookie) -> str:
        """获取 cookie 的友好名字，用于展示"""
        from . import text_fletten

        return text_fletten(f"{cookie.site_name} [{cookie.content[:10]}]")

    def _generate_hook(self, cookie: Cookie) -> callable:
        """hook 函数生成器，用于回写请求状态到数据库"""

        async def _response_hook(resp: httpx.Response):
            if resp.status_code == 200:
                logger.trace(f"请求成功: {cookie.id} {resp.request.url}")
                cookie.status = "success"
            else:
                logger.warning(f"请求失败:{cookie.id} {resp.request.url}, 状态码: {resp.status_code}")
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
        pass


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
    cookie_format_prompt = "无效的 Cookie，请检查后重新输入，详情见<待添加的文档>"

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


class SkipRequestException(Exception):
    pass
