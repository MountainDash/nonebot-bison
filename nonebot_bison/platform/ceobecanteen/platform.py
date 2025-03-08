from collections import defaultdict
from datetime import timedelta
from functools import partial
from typing import ClassVar, ParamSpec

from httpx import AsyncClient
from nonebot import logger, require
from rapidfuzz import fuzz, process

from nonebot_bison.platform.platform import NewMessage
from nonebot_bison.plugin_config import plugin_config
from nonebot_bison.post import Post
from nonebot_bison.types import Category, RawPost, Target
from nonebot_bison.utils import ClientManager, Site, capture_html

from .cache import CeobeCache, CeobeClient, CeobeDataSourceCache
from .const import COMB_ID_URL, COOKIE_ID_URL, COOKIES_URL
from .exception import CeobeSnapshotFailed, CeobeSnapshotSkip
from .models import CeobeCookie, CeobeImage, CeobeTextPic, CombIdResponse, CookieIdResponse, CookiesResponse
from .utils import process_response

P = ParamSpec("P")


class CeobeCanteenClientManager(ClientManager):
    _client: AsyncClient

    def __init__(self):
        self._client = CeobeClient(
            headers={
                "User-Agent": "MountainDash/Nonebot-Bison",
            }
        )

    async def get_client(self, target: Target | None) -> AsyncClient:
        return self._client

    async def get_client_for_static(self) -> AsyncClient:
        return self._client

    async def get_query_name_client(self) -> AsyncClient:
        return self._client

    async def refresh_client(self):
        raise NotImplementedError("refresh_client is not implemented")


class CeobeCanteenSite(Site):
    name = "ceobe_canteen"
    schedule_type = "interval"
    # lwt の 推荐间隔
    schedule_setting: ClassVar[dict] = {"seconds": 15}
    client_mgr = CeobeCanteenClientManager


class CeobeCanteen(NewMessage):
    enable_tag: bool = False
    platform_name: str = "ceobecanteen"
    name: str = "小刻食堂"
    enabled: bool = True
    is_common: bool = False
    site = CeobeCanteenSite
    has_target: bool = True
    use_batch: bool = True
    default_theme: str = "ceobecanteen"

    categories: ClassVar[dict[Category, str]] = {1: "普通", 2: "转发"}

    data_source_cache = CeobeDataSourceCache()

    comb_id = CeobeCache(timedelta(hours=12))
    cookie_id = CeobeCache(timedelta(hours=1))
    cookies = CeobeCache(timedelta(hours=1))

    async def get_comb_id(self, target_uuids: list[str]):
        """获取数据源的组合id"""
        payload = {"datasource_push": target_uuids}
        logger.trace(payload)
        client = await self.ctx.get_client()
        resp = await client.post(
            COMB_ID_URL,
            json=payload,
        )
        comb_id = process_response(resp, CombIdResponse).data["datasource_comb_id"]
        logger.trace(f"get comb_id: {comb_id}")
        return comb_id

    async def get_comb_id_of_all(self):
        """获取 "全部数据源" 的组合id，获取到的comb_id会缓存12小时"""
        logger.trace("no comb_id, request")
        target_uuids = (await self.data_source_cache.get_all()).keys()
        comb_id = await self.get_comb_id(list(target_uuids))

        logger.trace(f"use comb_id: {comb_id}")
        return comb_id

    async def get_latest_cookie_id(self, comb_id: str):
        """根据comb_id获取最新cookie_id"""
        client = await self.ctx.get_client()
        resp = await client.get(f"{COOKIE_ID_URL}/{comb_id}")
        cookie_id = process_response(resp, CookieIdResponse).cookie_id
        logger.trace(f"get cookie_id: {cookie_id}")
        return cookie_id

    async def get_cookies(self, cookie_id: str, comb_id: str | None = None):
        """根据cookie_id、comb_id组合获取cookies"""
        client = await self.ctx.get_client()
        parmas = {
            "datasource_comb_id": comb_id,
            "cookie_id": cookie_id,
        }
        logger.trace(f"will reuquest: {parmas}")
        resp = await client.get(COOKIES_URL, params=parmas)
        return process_response(resp, CookiesResponse).data.cookies

    async def fetch_ceobe_cookies(self) -> list[CeobeCookie]:
        if not self.comb_id:
            self.comb_id = await self.get_comb_id_of_all()

        latest_cookie_id = await self.get_latest_cookie_id(self.comb_id)
        if not latest_cookie_id:
            return []

        if latest_cookie_id != self.cookie_id:
            self.cookie_id = latest_cookie_id
            self.cookies = await self.get_cookies(latest_cookie_id, self.comb_id)

        return self.cookies or []

    async def batch_get_sub_list(self, targets: list[Target]) -> list[list[CeobeCookie]]:
        cookies = await self.fetch_ceobe_cookies()

        dispatched_cookies: defaultdict[Target, list[CeobeCookie]] = defaultdict(list)
        for cookie in cookies:
            if ceobe_target := await self.data_source_cache.get_by_source(cookie.source):
                dispatched_cookies[Target(ceobe_target.unique_id)].append(cookie)

        return [dispatched_cookies[target] for target in targets]

    @classmethod
    async def get_target_name(cls, _, uuid_target: Target) -> str:
        ceobe_target = await cls.data_source_cache.get_by_unique_id(uuid_target)
        return ceobe_target.nickname if ceobe_target else "UNKNOWN"

    @classmethod
    async def parse_target(cls, nickname: str) -> Target:
        ceobe_target = await cls.data_source_cache.get_by_nickname(nickname)
        if not ceobe_target:
            all_targets_name = [target.nickname for target in (await cls.data_source_cache.get_all()).values()]
            matched_targets_name = process.extract(nickname, all_targets_name, scorer=fuzz.token_sort_ratio, limit=3)
            logger.debug(f"possible targets: {matched_targets_name}")
            raise cls.ParseTargetException(
                prompt="未能匹配到对应的小刻食堂数据源，可能的选择有: \n"
                + "\n".join([name for name, *_ in matched_targets_name])
                + f"\n\n请检查原输入是否正确: {nickname}"
            )
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
        target = await self.data_source_cache.get_by_source(raw_post.source)
        assert target, "target not found"

        content, pics = await self.take_snapshot(raw_post)

        timestamp = raw_post.timestamp.platform or raw_post.timestamp.fetcher
        if timestamp:
            timestamp /= 1000  # 从毫秒级转换到秒级

        retweet: Post | None = None
        if raw_post.item.is_retweeted and raw_post.item.retweeted:
            raw_retweet_pics = raw_post.item.retweeted.images or []
            retweet_pics = await self.parse_retweet_images(raw_retweet_pics, raw_post.source.type)

            retweet = Post(
                self,
                nickname=raw_post.item.retweeted.author_name,
                avatar=raw_post.item.retweeted.author_avatar,
                images=list(retweet_pics),
                content=raw_post.item.retweeted.text,
            )

        return Post(
            self,
            content,
            url=raw_post.item.url,
            nickname=raw_post.datasource,
            images=list(pics),
            timestamp=timestamp,
            avatar=target.avatar,
            description=target.platform,
            repost=retweet,
        )

    async def snapshot_official_website(self, url: str) -> bytes:
        """截取小刻官网的截图"""
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import get_new_page

        logger.debug(f"snapshot official website url: {url}")

        # /html/body/div[1]/div[1]/div/div[1]/div[1]/div
        snapshot_selector = (
            "html > body > div:nth-child(1) > div:nth-child(1) > div > div:nth-child(1) > div:nth-child(1) > div"
        )
        # /html/body/div[1]/div[1]/div/div[1]/div[1]/div/div[4]/div/div/div
        calculate_selector = "html > body > div:nth-child(1) > div:nth-child(1) > div > div:nth-child(1) > div:nth-child(1) > div > div:nth-child(4) > div > div > div"  # noqa: E501
        viewport = {"width": 1024, "height": 19990}

        try:
            async with get_new_page(viewport=viewport) as page:
                await page.goto(url, wait_until="networkidle")
                element_width = await page.evaluate(
                    "(selector) => document.querySelector(selector).offsetWidth", calculate_selector
                )
                logger.debug(f"element width: {element_width}")
                element_height = await page.evaluate(
                    "(selector) => document.querySelector(selector).offsetHeight", calculate_selector
                )
                logger.debug(f"element height: {element_height}")
                element_height += 1000

                await page.set_viewport_size({"width": 1024, "height": element_height})

                element = await page.locator(snapshot_selector).element_handle()
                # add padding to make the screenshot more beautiful
                await element.evaluate("(element) => {element.style.padding = '20px';}", element)

                pic_data = await element.screenshot(
                    type="png",
                )
        except Exception as e:
            raise CeobeSnapshotFailed("渲染错误") from e
        else:
            return pic_data

    async def snapshot_bulletin_list(self, url: str) -> bytes:
        """截取小刻公告列表的截图"""
        selector = "body > div.main > div.container"
        viewport = {"width": 1024, "height": 19990}

        try:
            pic_data = await capture_html(
                url,
                selector,
                timeout=30000,
                wait_until="networkidle",
                viewport=viewport,
            )
            assert pic_data
        except Exception:
            raise CeobeSnapshotFailed("渲染错误")
        else:
            return pic_data

    async def take_snapshot(
        self,
        raw_post: CeobeCookie,
    ) -> CeobeTextPic:
        """判断数据源类型，判断是否需要截图"""

        match raw_post.source.type:
            case "arknights-website:official-website":

                async def owss(url: str) -> CeobeTextPic:
                    return CeobeTextPic(text="", pics=[await self.snapshot_official_website(url)])

                snapshot_func = partial(owss, raw_post.item.url)
            case "arknights-game:bulletin-list" if raw_post.item.display_type != 2:

                async def blss(url: str) -> CeobeTextPic:
                    return CeobeTextPic(text="", pics=[await self.snapshot_bulletin_list(url)])

                snapshot_func = partial(blss, raw_post.item.url)
            case _:

                async def npss() -> CeobeTextPic:
                    raise CeobeSnapshotSkip("无需截图的数据源")

                snapshot_func = partial(npss)

        raw_pics = raw_post.default_cookie.images or []
        try:
            if not plugin_config.bison_use_browser:
                raise CeobeSnapshotSkip("未启用浏览器")
            res = await snapshot_func()
        except CeobeSnapshotSkip as e:
            logger.info(f"skip snapshot: {e}")
            pics = await self.parse_retweet_images(raw_pics, raw_post.source.type)
            res = CeobeTextPic(text=raw_post.default_cookie.text, pics=list(pics))
        except CeobeSnapshotFailed:
            logger.exception("snapshot failed")
            pics = await self.parse_retweet_images(raw_pics, raw_post.source.type)
            res = CeobeTextPic(text=raw_post.default_cookie.text, pics=list(pics))

        return res

    async def parse_retweet_images(self, images: list[CeobeImage], source_type: str) -> list[bytes] | list[str]:
        if source_type.startswith("weibo"):
            retweet_pics = await self.download_weibo_image([image.origin_url for image in images])
        else:
            retweet_pics = [image.origin_url for image in images]
        return retweet_pics

    async def download_weibo_image(self, image_urls: list[str]) -> list[bytes]:
        headers = {"referer": "https://weibo.cn/"}
        pics = []
        async with CeobeClient(headers=headers) as client:
            for url in image_urls:
                resp = await client.get(url)
                resp.raise_for_status()
                pics.append(resp.content)
        return pics
