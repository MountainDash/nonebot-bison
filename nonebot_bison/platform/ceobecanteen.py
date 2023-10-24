from datetime import datetime
from typing import Literal, cast
from collections import defaultdict

from httpx import AsyncClient
from nonebot.log import logger
from pydantic import BaseModel
from expiringdict import ExpiringDict

from ..post import Post
from .platform import NewMessage
from ..types import Target, Category
from ..utils import SchedulerConfig, http_client

_datasource_cache = ExpiringDict(max_len=100, max_age_seconds=60 * 60 * 24)


class CeobeCanteenSchedConf(SchedulerConfig):
    name = "ceobecanteen"
    schedule_type = "interval"
    # lwt の 推荐间隔
    schedule_setting = {"seconds": 15}


class CeobeTarget(BaseModel):
    """账户结构"""

    avatar: str
    """数据源头像"""
    datasource: str
    """数据源类型"""
    db_unique_key: str
    """数据源相关唯一id"""
    nickname: str
    """数据源昵称"""
    platform: str
    """平台代码"""
    unique_id: str
    """数据源唯一标识（用于前后端交互标识）"""
    jump_url: str | None = None
    """跳转url（null就是没办法跳转）"""


class DataSourceResponse(BaseModel):
    code: int
    message: str
    data: list[CeobeTarget]


class CeobeImage(BaseModel):
    origin_url: str
    """原图"""
    compress_url: str | None = None
    """压缩图，为null就是没有原图对应压缩图"""


class CeobeDefaultCookie(BaseModel):
    text: str
    images: list[CeobeImage] | None


class CeobeRetweeted(BaseModel):
    author_name: str
    author_avatar: str
    text: str
    images: list[CeobeImage] | None = None


class CeobeItem(BaseModel):
    id: str
    """单条id"""
    url: str
    """跳转链接"""
    type: str
    """类型"""
    is_long_text: bool | None = None
    """是否长文"""
    is_retweeted: bool
    """是否转发"""
    retweeted: CeobeRetweeted | None = None

    class Config:
        extra = "allow"


class CeobeSource(BaseModel):
    data: str
    """数据源id"""
    type: str
    """数据源类型"""


class CeobeTimestamp(BaseModel):
    fetcher: int
    """蹲饼时间"""
    platform_precision: Literal["none", "day", "hour", "minute", "second", "ms"]
    """平台时间精度"""
    platform: int | None = None
    """平台时间戳"""


class CeobeCookie(BaseModel):
    datasource: str
    """数据源名字"""
    icon: str
    """数据源头像"""
    timestamp: CeobeTimestamp
    """时间戳"""
    default_cookie: CeobeDefaultCookie
    """原始饼"""
    item: CeobeItem
    """数据源信息，有平台的特殊字段"""
    source: CeobeSource
    """数据源"""


class CookiesResponse(BaseModel):
    code: int
    message: str
    data: list[CeobeCookie]


class CeobeCanteen(NewMessage):
    enable_tag: bool = False
    platform_name: str = "ceobecanteen"
    name: str = "小刻食堂"
    enabled: bool = True
    is_common: bool = False
    scheduler = CeobeCanteenSchedConf
    has_target: bool = True

    categories: dict[int, str] = {1: "普通", 2: "转发"}

    cached_comb_id: str | None = None
    cached_cookie_id: str | None = None
    cached_cookies: list[CeobeCookie] = []
    cached_targets: list[Target] = []
    last_modified: str | None = None

    async def is_target_changed(self, targets: list[Target]) -> bool:
        """判断target列表是否发生变化"""
        if self.cached_comb_id is None and targets:
            return True

        if len(targets) != len(self.cached_targets):
            return True

        return set(targets) != set(self.cached_targets)

    async def get_comb_id(self, targets: list[Target]):
        if not await self.is_target_changed(targets) and self.cached_comb_id is not None:
            return self.cached_comb_id

        payload = {"datasource_push": targets}
        comb_res = await self.client.post(
            "https://server.ceobecanteen.top/api/v1/canteen/user/getDatasourceComb", data=payload
        )
        comb_res.raise_for_status()
        comb_id: str = comb_res.json()["data"].get("datasource_comb_id", "<err>")
        if comb_id == "<err>":
            raise self.ParseTargetException(f"未找到对应组合Id: {targets}")
        self.cached_targets = targets
        self.cached_comb_id = comb_id
        return self.cached_comb_id

    async def get_cookie_id(self, comb_id: str):
        if self.cached_comb_id == comb_id and self.cached_cookie_id is not None:
            return self.cached_cookie_id

        cookie_res = await self.client.get(f"http://cdn-dev.ceobecanteen.top/datasource-comb/{comb_id}")
        cookie_res.raise_for_status()
        if "error" in cookie_res.json():
            raise self.ParseTargetException(f"未找到对应饼Id: {comb_id}")
        cookie_id = cookie_res.json()["cookie_id"]
        self.cached_cookie_id = cookie_id
        return self.cached_cookie_id

    async def get_cookies(self, comb_id: str, cookie_id: str):
        if self.cached_comb_id == comb_id and self.cached_cookie_id == cookie_id:
            return self.cached_cookies

        params = {
            "datasource_comb_id": comb_id,
            "cookie_id": cookie_id,
        }
        # 添加缓存头
        since_time = self.last_modified or datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers = {
            "If-Modified-Since": since_time,
        }
        data_res = await self.client.get(
            "https://server.ceobecanteen.top/api/v1/cdn/cookie/mainList/cookieList", params=params, headers=headers
        )
        if data_res.status_code == 304:
            self.last_modified = data_res.headers.get("Last-Modified")
            return self.cached_cookies
        data_res.raise_for_status()
        data = CookiesResponse.parse_obj(data_res.json())
        if data.code != "00000":
            raise self.ParseTargetException(f"获取饼数据失败: {data_res.json()}")
        self.cached_cookies = data.data
        self.last_modified = data_res.headers.get("Last-Modified")
        return self.cached_cookies

    @classmethod
    async def _refresh_datasource_cache(cls):
        res = await http_client.get("https://server.ceobecanteen.top/api/v1/canteen/config/datasource/list")
        res.raise_for_status()
        data = DataSourceResponse.parse_obj(res.json())
        if data.code != "00000":
            logger.warning(f"小刻食堂获取数据源列表失败: {data.message}")
            raise RuntimeError(f"小刻食堂获取数据源列表失败: {data.message}")
        for item in data.data:
            _datasource_cache[item.unique_id] = item
        return _datasource_cache

    @classmethod
    async def datasource_cache(cls, force_refresh: bool = False):
        if len(_datasource_cache) == 0 or force_refresh:
            await cls._refresh_datasource_cache()
        return _datasource_cache

    @classmethod
    async def get_datasource_by_name(cls, target_name: str) -> CeobeTarget | None:
        for target in await cls.datasource_cache():
            assert isinstance(target, CeobeTarget)
            if target.nickname == target_name:
                return cast(CeobeTarget, _datasource_cache[target])

        for target in await cls.datasource_cache(force_refresh=True):
            assert isinstance(target, CeobeTarget)
            if target.nickname == target_name:
                return cast(CeobeTarget, _datasource_cache[target])
        return None

    @classmethod
    async def get_datasource_by_uuid(cls, uuid: str) -> CeobeTarget | None:
        if uuid in await cls.datasource_cache():
            return cast(CeobeTarget, _datasource_cache[uuid])
        elif uuid in await cls.datasource_cache(force_refresh=True):
            return cast(CeobeTarget, _datasource_cache[uuid])
        return None

    @classmethod
    async def get_target_name(cls, _: AsyncClient, uuid_target: Target) -> str | None:
        ceobe_target = await cls.get_datasource_by_uuid(uuid_target)
        return ceobe_target.nickname if ceobe_target else None

    @classmethod
    async def parse_target(cls, target_string: str) -> Target:
        datasource = await cls.get_datasource_by_name(target_string)
        if datasource is None:
            logger.warning(f"小刻食堂未找到数据源: {target_string}")
            raise cls.ParseTargetException(f"小刻食堂未找到数据源: {target_string}")
        return Target(datasource.unique_id)

    async def get_uuid_by_cookie_source(self, source: CeobeSource):
        for target in await self.datasource_cache():
            assert isinstance(target, CeobeTarget)
            if target.db_unique_key == source.data and target.datasource == source.type:
                return target.unique_id

    async def batch_get_sub_list(self, targets: list[Target]) -> list[list[CeobeCookie]]:
        cookies = await self._get_cookies_by_targets(targets)
        dispatch_cookies: defaultdict[Target, list[CeobeCookie]] = defaultdict(list)
        for cookie in cookies:
            uuid = await self.get_uuid_by_cookie_source(cookie.source)
            if uuid is None:
                continue
            _target = Target(uuid)
            if _target not in dispatch_cookies:
                dispatch_cookies[_target] = []
            dispatch_cookies[_target].append(cookie)

        return [dispatch_cookies[target] for target in targets]

    async def _get_cookies_by_targets(self, targets: list[Target]):
        comb_id = await self.get_comb_id(targets)
        cookie_id = await self.get_cookie_id(comb_id)
        return await self.get_cookies(comb_id, cookie_id)

    def get_tags(self, _: CeobeCookie) -> None:
        return None

    def get_category(self, post: CeobeCookie) -> Category | None:
        if post.item.is_retweeted:
            return Category(2)
        else:
            return Category(1)

    def get_id(self, post: CeobeCookie) -> str:
        return post.item.id

    def get_date(self, post: CeobeCookie) -> int:
        return post.timestamp.fetcher

    async def parse(self, raw_post: CeobeCookie) -> Post:
        raw_pics = raw_post.default_cookie.images or []
        pics = [image.origin_url for image in raw_pics]
        return Post(
            self,
            raw_post.default_cookie.text,
            url=raw_post.item.url,
            nickname=raw_post.datasource,
            images=list(pics),
        )
