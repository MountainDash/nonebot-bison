from abc import ABC
from random import randint
from datetime import timedelta

from httpx import AsyncClient
from nonebot import logger, require
from playwright.async_api import Page, Cookie

from nonebot_bison.types import Target
from nonebot_bison.utils import SchedulerConfig, http_client

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_browser


class BilibiliClient:
    _client: AsyncClient
    _inited: bool = False
    cookie_expire_time = timedelta(hours=1)

    def __init__(self) -> None:
        self._client = http_client()

    async def _get_cookies(self) -> list[Cookie]:
        browser = await get_browser()
        page: Page = await browser.new_page()
        await page.goto(f"https://space.bilibili.com/{randint(1, 1000)}/dynamic")
        await page.wait_for_load_state("load")
        cookies = await page.context.cookies()
        await page.close()
        return cookies

    async def _reset_client_cookies(self, cookies: list[Cookie]):
        for cookie in cookies:
            self._client.cookies.set(
                name=cookie.get("name", ""),
                value=cookie.get("value", ""),
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/"),
            )

    async def refresh_client(self):
        cookies = await self._get_cookies()
        await self._reset_client_cookies(cookies)
        logger.debug("刷新B站客户端的cookie")

    async def get_client(self) -> AsyncClient:
        if not self._inited:
            logger.debug("初始化B站客户端")
            await self.refresh_client()
            self._inited = True
        return self._client


bilibili_client = BilibiliClient()


class BaseSchedConf(ABC, SchedulerConfig):
    schedule_type = "interval"
    bilibili_client: BilibiliClient

    def __init__(self):
        super().__init__()
        self.bilibili_client = bilibili_client

    async def get_client(self, _: Target) -> AsyncClient:
        return await self.bilibili_client.get_client()

    async def get_query_name_client(self) -> AsyncClient:
        return await self.bilibili_client.get_client()


class BilibiliSchedConf(BaseSchedConf):
    name = "bilibili.com"
    schedule_setting = {"seconds": 15}


class BililiveSchedConf(BaseSchedConf):
    name = "live.bilibili.com"
    schedule_setting = {"seconds": 15}
