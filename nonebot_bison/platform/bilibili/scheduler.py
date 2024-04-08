from abc import ABC
from random import randint
from datetime import datetime, timedelta

from httpx import AsyncClient
from nonebot import logger, require
from playwright.async_api import Page, Cookie

from nonebot_bison.types import Target
from nonebot_bison.utils import SchedulerConfig, http_client

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_browser


class BilibiliClient:
    _client: AsyncClient
    _cookie_refresh_time: datetime
    _pw_page: Page | None = None
    cookie_expire_time = timedelta(hours=1)

    def __init__(self) -> None:
        self._client = http_client()
        self._cookie_refresh_time = datetime(year=2000, month=1, day=1)  # an expired time

    async def _get_cookies(self) -> list[Cookie]:
        if self._pw_page:
            await self._pw_page.close()
        browser = await get_browser()
        page: Page = await browser.new_page()
        await page.goto(f"https://space.bilibili.com/{randint(1, 1000)}/dynamic")
        await page.wait_for_load_state("domcontentloaded")
        cookies = await page.context.cookies()
        self._pw_page = page
        return cookies

    async def _reset_client_cookies(self, cookies: list[Cookie]):
        self._client.cookies.clear()
        for cookie in cookies:
            self._client.cookies.set(
                name=cookie.get("name", ""),
                value=cookie.get("value", ""),
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/"),
            )

    async def refresh_client(self, force: bool = False):
        if force or datetime.now() - self._cookie_refresh_time > self.cookie_expire_time:
            cookies = await self._get_cookies()
            await self._reset_client_cookies(cookies)
            self._cookie_refresh_time = datetime.now()
            logger.debug("刷新B站客户端的cookie")
        else:
            logger.debug("不需要刷新B站客户端的cookie")

    async def get_client(self) -> AsyncClient:
        logger.debug("获取B站客户端")
        await self.refresh_client()
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
