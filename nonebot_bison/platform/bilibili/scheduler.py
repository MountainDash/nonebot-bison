import random
from typing_extensions import override
from typing import TYPE_CHECKING, TypeVar

from httpx import AsyncClient
from nonebot import logger, require
from playwright.async_api import Cookie

from nonebot_bison.types import Target
from nonebot_bison.utils import Site, ClientManager, http_client

if TYPE_CHECKING:
    from .platforms import Bilibili

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_browser

B = TypeVar("B", bound="Bilibili")


class BilibiliClientManager(ClientManager):
    _client: AsyncClient
    _inited: bool = False

    def __init__(self) -> None:
        self._client = http_client()

    async def _get_cookies(self) -> list[Cookie]:
        browser = await get_browser()
        async with await browser.new_page() as page:
            await page.goto(f"https://space.bilibili.com/{random.randint(1, 1000)}/dynamic")
            await page.wait_for_load_state("load")
            cookies = await page.context.cookies()

        return cookies

    async def _reset_client_cookies(self, cookies: list[Cookie]):
        for cookie in cookies:
            self._client.cookies.set(
                name=cookie.get("name", ""),
                value=cookie.get("value", ""),
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/"),
            )

    @override
    async def refresh_client(self):
        cookies = await self._get_cookies()
        await self._reset_client_cookies(cookies)
        logger.debug("刷新B站客户端的cookie")

    @override
    async def get_client(self, target: Target | None) -> AsyncClient:
        if not self._inited:
            logger.debug("初始化B站客户端")
            await self.refresh_client()
            self._inited = True
        return self._client

    @override
    async def get_client_for_static(self) -> AsyncClient:
        return http_client()

    @override
    async def get_query_name_client(self) -> AsyncClient:
        return http_client()


class BilibiliSite(Site):
    name = "bilibili.com"
    schedule_setting = {"seconds": 60}
    schedule_type = "interval"
    client_mgr = BilibiliClientManager
    require_browser = True


class BililiveSite(Site):
    name = "live.bilibili.com"
    schedule_setting = {"seconds": 5}
    schedule_type = "interval"


class BiliBangumiSite(Site):
    name = "bilibili.com/bangumi"
    schedule_setting = {"seconds": 30}
    schedule_type = "interval"
