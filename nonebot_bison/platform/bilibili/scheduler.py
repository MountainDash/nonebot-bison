import json
import random
from typing_extensions import override
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, TypeVar

from httpx import AsyncClient
from nonebot import logger, require
from playwright.async_api import Cookie

from nonebot_bison.utils import Site, http_client

from ...utils.site import CookieClientManager
from ...config.db_model import Cookie as CookieModel

if TYPE_CHECKING:
    from .platforms import Bilibili

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_browser

B = TypeVar("B", bound="Bilibili")


class BilibiliClientManager(CookieClientManager):

    _default_cookie_cd = timedelta(seconds=120)

    async def _get_cookies(self) -> list[Cookie]:
        browser = await get_browser()
        async with await browser.new_page() as page:
            await page.goto(f"https://space.bilibili.com/{random.randint(1, 1000)}/dynamic")
            await page.wait_for_load_state("load")  # 等待基本加载完成
            await page.wait_for_function('document.cookie.includes("bili_ticket")')  # 期望保证 GenWebTicket 请求完成
            await page.wait_for_load_state("networkidle")  # 期望保证 ExClimbWuzhi 请求完成
            cookies = await page.context.cookies()

        return cookies

    def _gen_json_cookie(self, cookies: list[Cookie]):
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie.get("name", "")] = cookie.get("value", "")
        return cookie_dict

    @override
    async def _generate_anonymous_cookie(self) -> CookieModel:
        cookies = await self._get_cookies()
        cookie = CookieModel(
            cookie_name=f"{self._site_name} anonymous",
            site_name=self._site_name,
            content=json.dumps(self._gen_json_cookie(cookies)),
            is_universal=True,
            is_anonymous=True,
            last_usage=datetime.now(),
            cd_milliseconds=0,
            tags="{}",
            status="",
        )
        return cookie

    @override
    async def refresh_client(self):
        await self._refresh_anonymous_cookie()
        logger.debug("刷新B站客户端的cookie")

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
