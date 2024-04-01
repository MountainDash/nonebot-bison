import traceback
from datetime import timedelta

from nonebot import logger, require

from ...post import Post
from ..platform import NewMessage
from .utils import process_response
from ...types import Target, RawPost, Category
from ...utils import SchedulerConfig, capture_html
from .const import COMB_ID_URL, COOKIES_URL, COOKIE_ID_URL
from .cache import CeobeCache, CeobeClient, CeobeDataSourceCache
from .models import CeobeImage, CeobeCookie, CombIdResponse, CookiesResponse, CookieIdResponse


class CeobeCanteenSchedConf(SchedulerConfig):
    name = "ceobe_canteen"
    schedule_type = "interval"
    # lwt の 推荐间隔
    schedule_setting = {"seconds": 15}

    def __init__(self):
        super().__init__()

        # 仅用于方便小刻食堂统计，没有实际影响
        headers = {
            "User-Agent": "MountainDash/Nonebot-Bison",
        }
        self.default_http_client = CeobeClient()
        self.default_http_client.headers.update(headers)


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

    comb_id = CeobeCache(timedelta(hours=12))
    cookie_id = CeobeCache(timedelta(hours=1))
    cookies = CeobeCache(timedelta(hours=1))

    async def get_comb_id(self, target_uuids: list[str]):
        """获取数据源的组合id"""
        payload = {"datasource_push": target_uuids}
        logger.trace(payload)
        resp = await self.client.post(
            COMB_ID_URL,
            json=payload,
        )
        comb_id = process_response(resp, CombIdResponse).data["datasource_comb_id"]
        logger.trace(f"get comb_id: {comb_id}")
        return comb_id

    async def get_comb_id_for_all(self):
        """获取 "全部数据源" 的组合id，获取到的comb_id会缓存12小时"""
        logger.trace("no comb_id, request")
        target_uuids = (await self.data_source_cache.get_all()).keys()
        comb_id = await self.get_comb_id(list(target_uuids))

        logger.debug(f"use comb_id: {comb_id}")
        return comb_id

    async def get_cookie_id(self, comb_id: str):
        """根据comb_id获取cookie_id"""
        resp = await self.client.get(f"{COOKIE_ID_URL}/{comb_id}")
        cookie_id = process_response(resp, CookieIdResponse).cookie_id
        logger.trace(f"get cookie_id: {cookie_id}")
        return cookie_id

    async def get_cookies(self, cookie_id: str, comb_id: str | None = None):
        """获取cookies"""
        parmas = {
            "datasource_comb_id": comb_id,
            "cookie_id": cookie_id,
        }
        logger.trace(f"will reuquest: {parmas}")
        resp = await self.client.get(COOKIES_URL, params=parmas)
        cookies = process_response(resp, CookiesResponse).data.cookies
        return cookies

    async def fetch_ceobe_cookies(self) -> list[CeobeCookie]:
        if not self.comb_id:
            comb_id = await self.get_comb_id_for_all()
            self.comb_id = comb_id

        cookie_id = await self.get_cookie_id(self.comb_id)
        if not cookie_id:
            return []

        if cookie_id != self.cookie_id:
            cookies = await self.get_cookies(cookie_id, self.comb_id)
            self.cookie_id = cookie_id
            self.cookies = cookies

        if not self.cookies:
            return []
        return self.cookies

    async def batch_get_sub_list(self, targets: list[Target]) -> list[list[CeobeCookie]]:
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

        match raw_post.source.type:
            case "arknights-website:official-website":
                content = ""
                pics = await self._ceobecanteen_render(
                    raw_post.item.url,
                    "body > div.article-page > div.layout > div.layoutContent > div",
                    viewport={"width": 1024, "height": 19990},
                )
            case "arknights-game:bulletin-list" if raw_post.item.display_type != 2:
                content = ""
                pics = await self._ceobecanteen_render(
                    raw_post.item.url,
                    "body > div.main > div.container",
                )
            case _:
                pics = await self.handle_images_list(raw_pics, raw_post.source.type)
                content = raw_post.default_cookie.text

        timestamp = raw_post.timestamp.platform or raw_post.timestamp.fetcher
        if timestamp:
            timestamp /= 1000  # 从毫秒级转换到秒级

        retweet: Post | None = None
        if raw_post.item.is_retweeted and raw_post.item.retweeted:
            raw_retweet_pics = raw_post.item.retweeted.images or []
            retweet_pics = await self.handle_images_list(raw_retweet_pics, raw_post.source.type)

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

    async def _ceobecanteen_render(
        self,
        url: str,
        selector: str,
        device_scale_factor: int = 2,
        viewport: dict = {"width": 1024, "height": 512},
    ) -> list[bytes]:
        """
        将给定的url网页的指定CSS选择器部分渲染成图片
        """
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import text_to_pic

        try:
            assert url
            pic_data = await capture_html(
                url,
                selector,
                timeout=30000,
                wait_until="networkidle",
                viewport=viewport,
                device_scale_factor=device_scale_factor,
            )
            assert pic_data
        except Exception:
            err_info = traceback.format_exc()
            logger.warning(f"渲染错误：{err_info}")

            err_pic0 = await text_to_pic("错误发生！")
            err_pic1 = await text_to_pic(err_info)
            return [err_pic0, err_pic1]
        else:
            return [pic_data]

    async def handle_images_list(self, images: list[CeobeImage], source_type: str) -> list[bytes] | list[str]:
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
