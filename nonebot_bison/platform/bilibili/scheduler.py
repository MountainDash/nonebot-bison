from collections.abc import Callable
from datetime import datetime, timedelta
import json
import random
from typing import TYPE_CHECKING, ClassVar, TypeVar
from typing_extensions import override

from httpx import AsyncClient, Response
from nonebot import logger, require
from playwright.async_api import Cookie

from nonebot_bison.config import config
from nonebot_bison.config.db_model import Cookie as CookieModel
from nonebot_bison.config.db_model import Target
from nonebot_bison.plugin_config import plugin_config
from nonebot_bison.utils import Site, http_client
from nonebot_bison.utils.site import CookieClientManager

if TYPE_CHECKING:
    from .platforms import Bilibili

if plugin_config.bison_use_browser:
    require("nonebot_plugin_htmlrender")
    from nonebot_plugin_htmlrender import get_browser

B = TypeVar("B", bound="Bilibili")


class BilibiliClientManager(CookieClientManager):
    _default_cookie_cd = timedelta(seconds=120)
    current_identified_cookie: CookieModel | None = None
    _site_name = "bilibili.com"

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

    def _generate_hook(self, cookie: CookieModel) -> Callable:
        """hook 函数生成器，用于回写请求状态到数据库"""

        async def _response_hook(resp: Response):
            await resp.aread()
            if resp.status_code == 200 and "-352" not in resp.text:
                logger.trace(f"请求成功: {cookie.id} {resp.request.url}")
                cookie.status = "success"
            else:
                logger.warning(f"请求失败: {cookie.id} {resp.request.url}, 状态码: {resp.status_code}")
                cookie.status = "failed"
                self.current_identified_cookie = None
            cookie.last_usage = datetime.now()
            await config.update_cookie(cookie)

        return _response_hook

    async def _get_next_identified_cookie(self) -> CookieModel | None:
        """选择下一个实名 cookie"""
        cookies = await config.get_cookie(self._site_name, is_anonymous=False)
        available_cookies = [cookie for cookie in cookies if cookie.last_usage + cookie.cd < datetime.now()]
        if not available_cookies:
            return None
        cookie = min(available_cookies, key=lambda x: x.last_usage)
        return cookie

    async def _choose_cookie(self, target: Target | None) -> CookieModel:
        """选择 cookie 的具体算法"""
        if self.current_identified_cookie is None:
            # 若当前没有选定实名 cookie 则尝试获取
            self.current_identified_cookie = await self._get_next_identified_cookie()
        if self.current_identified_cookie:
            # 如果当前有选定的实名 cookie 则直接返回
            return self.current_identified_cookie
        # 否则返回匿名 cookie
        return (await config.get_cookie(self._site_name, is_anonymous=True))[0]

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
    schedule_setting: ClassVar[dict] = {"seconds": 60}
    schedule_type = "interval"
    client_mgr = BilibiliClientManager
    require_browser = True


class BililiveSite(Site):
    name = "live.bilibili.com"
    schedule_setting: ClassVar[dict] = {"seconds": 5}
    schedule_type = "interval"


class BiliBangumiSite(Site):
    name = "bilibili.com/bangumi"
    schedule_setting: ClassVar[dict] = {"seconds": 30}
    schedule_type = "interval"
