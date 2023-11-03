from typing import cast
from datetime import timedelta

from nonebot import logger
from hishel import AsyncCacheClient

from ...post import Post
from ..platform import NewMessage
from .utils import process_response
from ...utils import SchedulerConfig
from ...types import Target, RawPost, Category
from .const import COMB_ID_URL, COOKIES_URL, COOKIE_ID_URL
from .cache import CeobeClient, SimpleCache, CeobeDataSourceCache
from .models import CeobeCookie, CombIdResponse, CookiesResponse, CookieIdResponse


class CeobeCanteenSchedConf(SchedulerConfig):
    name = "ceobe_canteen"
    schedule_type = "interval"
    # lwt の 推荐间隔
    schedule_setting = {"seconds": 15}

    def __init__(self):
        super().__init__()
        self.default_http_client = CeobeClient()


class CeobeCanteen(NewMessage):
    enable_tag: bool = False
    platform_name: str = "ceobecanteen"
    name: str = "小刻食堂"
    enabled: bool = True
    is_common: bool = False
    scheduler = CeobeCanteenSchedConf
    has_target: bool = True
    use_batch: bool = True
    default_theme: str = "ceobecanteen"

    categories: dict[Category, str] = {1: "普通", 2: "转发"}

    data_source_cache = CeobeDataSourceCache()
    cache_store = SimpleCache()

    async def get_comb_id(self, targets: list[Target] | None = None, force_refresh: bool = False) -> str | None:
        """获取数据源的组合id

        如果不传入targets, 则请求所有数据源的组合id
        """
        if self.cache_store["comb_id"] is None or force_refresh:
            logger.trace("no comb_id, request")
            target_uuids = targets or (await self.data_source_cache.get_all()).keys()
            payload = {"datasource_push": list(target_uuids)}
            logger.trace(payload)
            resp = await self.client.post(
                COMB_ID_URL,
                json=payload,
            )
            comb_id = process_response(resp, CombIdResponse).data["datasource_comb_id"]
            logger.trace(f"get comb_id: {comb_id}")
            self.cache_store["comb_id"] = (comb_id, timedelta(hours=12))

        return self.cache_store["comb_id"]

    async def get_cookie_id(self, comb_id: str):
        """根据comb_id获取cookie_id"""
        resp = await self.client.get(f"{COOKIE_ID_URL}/{comb_id}")
        cookie_id = process_response(resp, CookieIdResponse).cookie_id
        logger.trace(f"get cookie_id: {cookie_id}")
        return cookie_id

    async def get_cookies(self, cookie_id: str, comb_id: str | None = None, force_refresh: bool = False):
        """获取cookies"""

        async def request():
            parmas = {
                "datasource_comb_id": comb_id or self.cache_store["comb_id"],
                "cookie_id": cookie_id,
            }
            logger.trace(f"will reuquest: {parmas}")
            resp = await self.client.get(COOKIES_URL, params=parmas)
            cookies = process_response(resp, CookiesResponse).data.cookies
            return cookies

        def update(cookie_id: str, cookies: list[CeobeCookie]):
            lifetime = timedelta(hours=1)
            self.cache_store["cookie_id"] = (cookie_id, lifetime)
            self.cache_store["cookies"] = (cookies, lifetime)

        if cookie_id != self.cache_store["cookie_id"] or force_refresh:
            logger.trace(f"cookie_id changed: {self.cache_store['cookie_id']} -> {cookie_id}, request cookies")
            cookies = await request()
            update(cookie_id, cookies)
        elif self.cache_store["cookies"] is None:
            logger.trace("no cookie_id, update")
            cookies = await request()
            update(cookie_id, cookies)
        else:
            logger.trace(f"cookoe_id no change, {self.cache_store['cookie_id']}")

        logger.trace(f"now cookie_id is {self.cache_store['cookie_id']}")
        return cast(list[CeobeCookie] | None, self.cache_store["cookies"])

    async def fetch_ceobe_cookies(self) -> list[CeobeCookie]:
        comb_id = await self.get_comb_id()
        if not comb_id:
            return []
        cookie_id = await self.get_cookie_id(comb_id)
        cookies = await self.get_cookies(cookie_id)
        if not cookies:
            return []
        return cookies

    async def batch_get_sub_list(self, targets: list[Target]) -> list[list[CeobeCookie]]:
        if not isinstance(self.client, AsyncCacheClient):
            logger.warning("小刻食堂请求未使用AsyncCacheClient, 无法使用缓存，请反馈")

        cookies = await self.fetch_ceobe_cookies()

        dispatched_cookies: dict[Target, list[CeobeCookie]] = {}
        for cookie in cookies:
            ceobe_target = await self.data_source_cache.get_by_source(cookie.source)
            if not ceobe_target:
                continue
            target = Target(ceobe_target.unique_id)
            if target not in dispatched_cookies:
                dispatched_cookies[target] = []
            dispatched_cookies[target].append(cookie)

        return [dispatched_cookies.get(target, []) for target in targets]

    @classmethod
    async def get_target_name(cls, _, uuid_target: Target) -> str:
        ceobe_target = await cls.data_source_cache.get_by_unique_id(uuid_target)
        return ceobe_target.nickname if ceobe_target else "UNKNOWN"

    @classmethod
    async def parse_target(cls, nickname: str) -> Target:
        ceobe_target = await cls.data_source_cache.get_by_nickname(nickname)
        if not ceobe_target:
            raise cls.ParseTargetException(f"未找到小刻食堂数据源: {nickname}")
        return Target(ceobe_target.unique_id)

    def get_tags(self, _: RawPost) -> None:
        return

    def get_category(self, post: CeobeCookie) -> Category:
        if post.item.is_retweeted:
            return Category(2)
        return Category(1)

    def get_id(self, post: CeobeCookie) -> str:
        return post.item.id

    def get_date(self, post: CeobeCookie) -> int:
        return post.timestamp.fetcher

    async def parse(self, raw_post: CeobeCookie) -> Post:
        raw_pics = raw_post.default_cookie.images or []
        target = await self.data_source_cache.get_by_source(raw_post.source)
        assert target, "target not found"

        if raw_post.source.type.startswith("weibo"):
            pics = await self.download_weibo_image([image.origin_url for image in raw_pics])
        else:
            pics = [image.origin_url for image in raw_pics]
        timestamp = raw_post.timestamp.platform or raw_post.timestamp.fetcher
        if timestamp:
            timestamp /= 1000  # 从毫秒级转换到秒级
        return Post(
            self,
            raw_post.default_cookie.text,
            url=raw_post.item.url,
            nickname=raw_post.datasource,
            images=list(pics),
            timestamp=timestamp,
            avatar=target.avatar,
            description=target.platform,
        )

    async def download_weibo_image(self, image_urls: list[str]) -> list[bytes]:
        headers = {"referer": "https://weibo.cn/"}
        pics = []
        async with CeobeClient(headers=headers) as client:
            for url in image_urls:
                resp = await client.get(url)
                resp.raise_for_status()
                pics.append(resp.content)
        return pics
