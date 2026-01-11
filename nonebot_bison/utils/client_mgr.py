from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import json
from typing import override

import httpx
from httpx import AsyncClient
from nonebot import logger

from nonebot_bison.core.site import ClientManager
from nonebot_bison.db import data_access
from nonebot_bison.db.db_model import Cookie
from nonebot_bison.typing import Target
from nonebot_bison.utils.http import http_client
from nonebot_bison.utils.text import text_fletten


class DefaultClientManager(ClientManager):
    @override
    async def get_client(self, target: Target | None) -> AsyncClient:
        return http_client()

    @override
    async def get_client_for_static(self) -> AsyncClient:
        return http_client()

    @override
    async def get_query_name_client(self) -> AsyncClient:
        return http_client()

    @override
    async def refresh_client(self):
        pass

    @override
    async def on_init_scheduler(self):
        pass


class SkipRequestException(Exception):
    """跳过请求异常，如果需要在选择 Cookie 时跳过此次请求，可以抛出此异常"""

    pass


class CookieClientManager(ClientManager):
    _default_cookie_cd = timedelta(seconds=15)
    _site_name: str = ""

    async def _generate_anonymous_cookie(self) -> Cookie:
        return Cookie(
            cookie_name=f"{self._site_name} anonymous",
            site_name=self._site_name,
            content="{}",
            is_universal=True,
            is_anonymous=True,
            last_usage=datetime.now(tz=UTC),
            cd_milliseconds=0,
            tags="{}",
            status="",
        )

    async def _refresh_anonymous_cookie(self):
        """更新已有的匿名cookie，若不存在则添加"""
        existing_anonymous_cookies = await data_access.get_cookie(
            self._site_name, is_anonymous=True
        )
        if existing_anonymous_cookies:
            for cookie in existing_anonymous_cookies:
                new_anonymous_cookie = await self._generate_anonymous_cookie()
                new_anonymous_cookie.id = cookie.id  # 保持原有的id
                await data_access.update_cookie(new_anonymous_cookie)
        else:
            new_anonymous_cookie = await self._generate_anonymous_cookie()
            await data_access.add_cookie(new_anonymous_cookie)

    async def add_identified_cookie(
        self, content: str, cookie_name: str | None = None
    ) -> Cookie:
        """添加实名 cookie"""

        if not await self.validate_cookie(content):
            raise ValueError()
        cookie = Cookie(site_name=self._site_name, content=content)
        cookie.cookie_name = (
            cookie_name if cookie_name else await self.get_cookie_name(content)
        )
        cookie.cd = self._default_cookie_cd
        cookie_id = await data_access.add_cookie(cookie)
        return await data_access.get_cookie_by_id(cookie_id)

    async def get_cookie_name(self, content: str) -> str:
        """从cookie内容中获取cookie的友好名字，添加cookie时调用，持久化在数据库中"""
        return text_fletten(f"{self._site_name} [{content[:10]}]")

    async def validate_cookie(self, content: str) -> bool:
        """验证 cookie 内容是否有效，添加 cookie 时用，可根据平台的具体情况进行重写"""
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                return False
        except json.JSONDecodeError:
            return False
        return True

    def _generate_hook(self, cookie: Cookie) -> Callable:
        """hook 函数生成器，用于回写请求状态到数据库"""

        async def _response_hook(resp: httpx.Response):
            if resp.status_code == 200:
                logger.trace(f"请求成功: {cookie.id} {resp.request.url}")
                cookie.status = "success"
            else:
                logger.warning(
                    f"请求失败: {cookie.id} {resp.request.url}, 状态码: {resp.status_code}"
                )
                cookie.status = "failed"
            cookie.last_usage = datetime.now(tz=UTC)
            await data_access.update_cookie(cookie)

        return _response_hook

    async def _choose_cookie(self, target: Target | None) -> Cookie:
        """选择 cookie 的具体算法"""
        cookies = await data_access.get_cookie(self._site_name, target)
        available_cookies = (
            cookie
            for cookie in cookies
            if cookie.last_usage + cookie.cd < datetime.now(tz=UTC)
        )
        cookie = min(available_cookies, key=lambda x: x.last_usage)
        return cookie

    async def get_client(self, target: Target | None) -> AsyncClient:
        """获取 client，根据 target 选择 cookie"""
        client = http_client()
        cookie = await self._choose_cookie(target)
        # FIXME: 实现指标统计
        # cookie_choose_counter.labels(site_name=self._site_name, target=target, cookie_id=cookie.id).inc()
        if cookie.is_universal:
            logger.trace(f"平台 {self._site_name} 未获取到实名cookie, 使用匿名cookie")
        else:
            logger.trace(f"平台 {self._site_name} 获取到实名cookie: {cookie.id}")

        return await self._assemble_client(client, cookie)

    async def _assemble_client(self, client, cookie) -> AsyncClient:
        """组装 client，可以自定义 cookie 对象装配到 client 中的方式"""
        cookies = httpx.Cookies()
        if cookie:
            cookies.update(json.loads(cookie.content))
        client.cookies = cookies
        client.event_hooks = {"response": [self._generate_hook(cookie)]}
        return client

    @classmethod
    def from_name(cls, site_name: str) -> type["CookieClientManager"]:
        """创建一个平台特化的 CookieClientManger"""
        return type(
            "CookieClientManager",
            (CookieClientManager,),
            {"_site_name": site_name},
        )

    async def get_client_for_static(self) -> AsyncClient:
        return http_client()

    async def get_query_name_client(self) -> AsyncClient:
        return http_client()

    async def refresh_client(self):
        await self._refresh_anonymous_cookie()
