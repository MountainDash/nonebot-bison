import json
import random
from typing_extensions import override
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, TypeVar

from httpx import AsyncClient
from nonebot import logger, require
from playwright.async_api import Cookie

from nonebot_bison.utils import Site, http_client

from ...config.db_model import Cookie as CookieModel
from ...utils.site import CookieSite, CookieClientManager

if TYPE_CHECKING:
    from .platforms import Bilibili

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_browser

B = TypeVar("B", bound="Bilibili")


class BilibiliClientManager(CookieClientManager):
    _client: AsyncClient
    _inited: bool = False

    _site_name: str = "bilibili.com"

    def __init__(self) -> None:
        self._client = http_client()

    @classmethod
    async def _get_cookies(self) -> list[Cookie]:
        browser = await get_browser()
        async with await browser.new_page() as page:
            await page.goto(f"https://space.bilibili.com/{random.randint(1, 1000)}/dynamic")
            await page.wait_for_load_state("load")  # 等待基本加载完成
            await page.wait_for_function('document.cookie.includes("bili_ticket")')  # 期望保证 GenWebTicket 请求完成
            await page.wait_for_load_state("networkidle")  # 期望保证 ExClimbWuzhi 请求完成
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

    @classmethod
    def _gen_json_cookie(self, cookies: list[Cookie]):
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie.get("name", "")] = cookie.get("value", "")
        return cookie_dict

    @classmethod
    @override
    async def _generate_anonymous_cookie(cls) -> CookieModel:
        cookies = await cls._get_cookies()
        cookie = CookieModel(
            cookie_name=f"{cls._site_name} anonymous",
            site_name=cls._site_name,
            content=json.dumps(cls._gen_json_cookie(cookies)),
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


class BilibiliSite(CookieSite):
    name = "bilibili.com"
    schedule_setting = {"seconds": 60}
    schedule_type = "interval"
    client_mgr = BilibiliClientManager
    require_browser = True
    default_cookie_cd: int = timedelta(seconds=120)


class BililiveSite(Site):
    name = "live.bilibili.com"
    schedule_setting = {"seconds": 5}
    schedule_type = "interval"


class BiliBangumiSite(Site):
    name = "bilibili.com/bangumi"
    schedule_setting = {"seconds": 30}
    schedule_type = "interval"
