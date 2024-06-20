from enum import Enum
from random import randint
from functools import wraps
from typing_extensions import override
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, TypeVar
from collections.abc import Callable, Awaitable

from httpx import AsyncClient
from httpx import URL as HttpxURL
from nonebot import logger, require
from playwright.async_api import Cookie

from nonebot_bison.types import Target, ApiError
from nonebot_bison.utils import Site, ClientManager, http_client

from .models import DynRawPost

if TYPE_CHECKING:
    from .platforms import Bilibili

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import get_browser

B = TypeVar("B", bound="Bilibili")


class ApiCode352Error(Exception):
    def __init__(self, url: HttpxURL) -> None:
        msg = f"api {url} error"
        super().__init__(msg)


class ScheduleLevel(Enum):
    NORMAL = 0
    REFRESH = 1
    BACKOFF = 2
    RAISE = 3

    @staticmethod
    def level_up(level: "ScheduleLevel"):
        if level.value == ScheduleLevel.RAISE.value:
            return ScheduleLevel.RAISE
        return ScheduleLevel(level.value + 1)


class ScheduleState:
    MAX_REFRESH_COUNT = 3
    MAX_BACKOFF_COUNT = 2
    BACKOFF_TIMEDELTA = timedelta(minutes=5)

    current_times: int
    level: ScheduleLevel
    backoff_start_time: datetime
    latest_normal_return: list[DynRawPost] = []

    def __init__(self):
        self.current_times = 1
        self.level = ScheduleLevel.NORMAL

    def increase(self):
        match self.level:
            case ScheduleLevel.NORMAL:
                logger.warning("获取动态列表失败，进入刷新cookie状态")
                self.level = ScheduleLevel.level_up(self.level)
            case ScheduleLevel.REFRESH if self.current_times < self.MAX_REFRESH_COUNT:
                self.current_times += 1
                logger.warning(
                    f"本次刷新后获取动态列表失败，下次请求前再次尝试刷新cookie：{self.current_times}/{self.MAX_REFRESH_COUNT}"
                )
            case ScheduleLevel.REFRESH if self.current_times >= self.MAX_REFRESH_COUNT:
                self.current_times = 1
                logger.trace(f"set backoff_start_time: {datetime.now()} in REFRESH level up")
                logger.warning("刷新cookie失败，进行回避状态")
                self.backoff_start_time = datetime.now()
                self.level = ScheduleLevel.level_up(self.level)
            case ScheduleLevel.BACKOFF if self.current_times < self.MAX_BACKOFF_COUNT:
                self.current_times += 1
                logger.trace(f"set backoff_start_time: {datetime.now()} in BACKOFF level")
                logger.warning(
                    f"上次回避尝试失败，等待下次尝试({self.current_times}/{self.MAX_BACKOFF_COUNT})，预计等待 "
                    f"{self.BACKOFF_TIMEDELTA * self.current_times ** 2}"
                )
                self.backoff_start_time = datetime.now()
            case ScheduleLevel.BACKOFF if self.current_times >= self.MAX_BACKOFF_COUNT:
                self.current_times = 1
                self.level = ScheduleLevel.level_up(self.level)
                logger.error("获取动态列表失败，尝试刷新cookie失败，尝试回避失败，放弃")
            case ScheduleLevel.RAISE:
                logger.critical("Already in RAISE level")
            case _:
                raise ValueError("ScheduleLevel Error")

    def reset(self):
        self.current_times = 1
        self.level = ScheduleLevel.NORMAL

    def is_in_backoff_time(self):
        """是否在指数回避时间内"""
        # 指数回避
        logger.trace(f"current_times: {self.current_times}")
        logger.trace(f"backoff_start_time: {self.backoff_start_time}")
        logger.trace(f"now: {datetime.now()}")
        logger.trace(f"delta: {datetime.now() - self.backoff_start_time}")
        logger.trace(f"wait: {self.BACKOFF_TIMEDELTA * self.current_times ** 2}")

        res = datetime.now() - self.backoff_start_time < self.BACKOFF_TIMEDELTA * self.current_times**2

        logger.trace(f"result: {res}")
        return res


def retry_for_352(func: Callable[[B, Target], Awaitable[list[DynRawPost]]]):
    schedule_state = ScheduleState()

    @wraps(func)
    async def wrapper(bls: B, *args, **kwargs):
        nonlocal schedule_state
        try:
            match schedule_state.level:
                case ScheduleLevel.BACKOFF if schedule_state.is_in_backoff_time():
                    logger.warning("回避中，本次不进行请求")
                    return schedule_state.latest_normal_return
                case ScheduleLevel.BACKOFF | ScheduleLevel.REFRESH:
                    logger.debug("尝试刷新客户端")
                    await bls.ctx.refresh_client()

            res = await func(bls, *args, **kwargs)
        except ApiCode352Error as e:
            schedule_state.increase()
            match schedule_state.level:
                case ScheduleLevel.RAISE:
                    raise ApiError(e.args[0]) from e
                case _:
                    return schedule_state.latest_normal_return
        else:
            schedule_state.reset()
            schedule_state.latest_normal_return = res
            return res

    return wrapper


class BilibiliClientManager(ClientManager):
    _client: AsyncClient
    _inited: bool = False

    def __init__(self) -> None:
        self._client = http_client()

    async def _get_cookies(self) -> list[Cookie]:
        browser = await get_browser()
        async with await browser.new_page() as page:
            await page.goto(f"https://space.bilibili.com/{randint(1, 1000)}/dynamic")
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
