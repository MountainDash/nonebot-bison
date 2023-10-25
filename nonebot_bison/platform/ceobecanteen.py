from collections import defaultdict
from typing import Literal, TypeVar, cast

from nonebot.log import logger
from pydantic import BaseModel
from hishel import AsyncCacheClient
from expiringdict import ExpiringDict
from httpx import Response, AsyncClient

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

    def __init__(self):
        self.default_http_client = AsyncCacheClient(headers={"Bot": "Nonebot-Bison"})


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


class CeobeData(BaseModel):
    cookies: list[CeobeCookie]
    next_page_id: str | None = None


class CookiesResponse(BaseModel):
    code: int
    message: str
    data: CeobeData


class CombIdResponse(BaseModel):
    code: int
    message: str
    data: dict[Literal["datasource_comb_id"], str]


class CookieIdResponse(BaseModel):
    cookie_id: str
    update_cookie_id: str


ResponseModel = TypeVar("ResponseModel", bound=CookiesResponse | CombIdResponse | CookieIdResponse)


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

    categories: dict[int, str] = {1: "普通", 2: "转发"}

    cached_comb_id: str | None = None
    cached_cookie_id: str | None = None
    cached_cookies: list[CeobeCookie] = []
    cached_targets: list[Target] = []

    async def is_target_changed(self, targets: list[Target]) -> bool:
        """判断target列表是否发生变化"""
        if self.cached_comb_id is None and targets:
            return True

        if len(targets) != len(self.cached_targets):
            return True

        return set(targets) != set(self.cached_targets)

    def process_response(self, response: Response, parse_model: type[ResponseModel]) -> ResponseModel:
        response.raise_for_status()
        logger.trace(f"小刻食堂请求结果: {response.json().get('message')} {parse_model=}")
        data = parse_model.parse_obj(response.json())
        if not isinstance(data, CookieIdResponse) and data.code != 0:
            raise self.ParseTargetException(f"获取饼数据失败: {data.message}")
        return data

    async def get_comb_id(self, targets: list[Target]):
        if not await self.is_target_changed(targets) and self.cached_comb_id is not None:
            logger.trace(f"小刻食堂组合Id未发生变化, 使用缓存: {self.cached_comb_id}")
            return self.cached_comb_id

        payload = {"datasource_push": targets}
        logger.trace(f"请求comb_id: {payload}")
        comb_res = await self.client.post(
            "https://server.ceobecanteen.top/api/v1/canteen/user/getDatasourceComb", json=payload
        )

        comb_id = self.process_response(comb_res, CombIdResponse).data["datasource_comb_id"]
        if not comb_id:
            raise self.ParseTargetException(f"未找到对应组合Id: {targets}")
        self.cached_targets = targets
        return comb_id

    async def get_cookie_id(self, comb_id: str):
        cookie_res = await self.client.get(f"http://cdn.ceobecanteen.top/datasource-comb/{comb_id}")
        cookie_id = self.process_response(cookie_res, CookieIdResponse).cookie_id
        return cookie_id

    async def get_cookies(self, comb_id: str, cookie_id: str):
        params = {
            "datasource_comb_id": comb_id,
            "cookie_id": cookie_id,
        }
        data_res = await self.client.get(
            "https://server-cdn.ceobecanteen.top/api/v1/cdn/cookie/mainList/cookieList", params=params
        )

        cookies = self.process_response(data_res, CookiesResponse).data.cookies
        return cookies

    @classmethod
    async def _refresh_datasource_cache(cls):
        res = await http_client().get("https://server.ceobecanteen.top/api/v1/canteen/config/datasource/list")
        res.raise_for_status()
        data = DataSourceResponse.parse_obj(res.json())
        logger.debug(f"小刻食堂获取数据源列表: {len(data.data)}")
        if data.code != 0:
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
        datasources = await cls.datasource_cache()
        for uuid, target in datasources.items():
            logger.debug(f"小刻食堂target: {target}")
            assert isinstance(target, CeobeTarget)
            if target.nickname == target_name:
                return cast(CeobeTarget, _datasource_cache[uuid])

        for uuid, target in await cls.datasource_cache(force_refresh=True):
            assert isinstance(target, CeobeTarget)
            if target.nickname == target_name:
                return cast(CeobeTarget, _datasource_cache[uuid])
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
    async def parse_target(cls, target_nickname: str) -> Target:
        datasource = await cls.get_datasource_by_name(target_nickname)
        if datasource is None:
            logger.warning(f"小刻食堂未找到数据源: {target_nickname}")
            raise cls.ParseTargetException(f"小刻食堂未找到数据源: {target_nickname}")
        return Target(datasource.unique_id)

    async def get_uuid_by_cookie_source(self, source: CeobeSource):
        for target_uuid in await self.datasource_cache():
            assert isinstance(target_uuid, str)
            target = _datasource_cache[target_uuid]
            assert isinstance(target, CeobeTarget)
            if target.db_unique_key == source.data and target.datasource == source.type:
                return target.unique_id

    async def batch_get_sub_list(self, targets: list[Target]) -> list[list[CeobeCookie]]:
        if not isinstance(self.client, AsyncCacheClient):
            logger.warning("小刻食堂缓存客户端不是AsyncCacheClient, 无法使用缓存，请反馈")

        cookies = await self._get_cookies_by_targets(targets)
        logger.trace(f"获取小刻食堂饼列表: {len(cookies)}")
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

    async def _get_cookies_by_targets(self, targets: list[Target]) -> list[CeobeCookie]:
        logger.trace(f"小刻食堂缓存: {self.cached_comb_id=} {self.cached_cookie_id=} {len(self.cached_cookies)=}")
        comb_id = await self.get_comb_id(targets)
        cookie_id = await self.get_cookie_id(comb_id)
        if self.cached_cookie_id == cookie_id:
            logger.trace(f"小刻食堂cookie_id未发生变化, 使用缓存: {cookie_id}")
            return self.cached_cookies

        cookies = await self.get_cookies(comb_id, cookie_id)

        self.cached_comb_id = comb_id
        self.cached_cookie_id = cookie_id
        self.cached_cookies = cookies
        logger.trace(f"获取后小刻食堂缓存: {self.cached_comb_id=} {self.cached_cookie_id=} {len(self.cached_cookies)=}")

        return cookies

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
        uuid = await self.get_uuid_by_cookie_source(raw_post.source)
        target = await self.get_datasource_by_uuid(uuid) if uuid else None
        return Post(
            self,
            raw_post.default_cookie.text,
            url=raw_post.item.url,
            nickname=raw_post.datasource,
            images=list(pics),
            timestamp=raw_post.timestamp.platform or raw_post.timestamp.fetcher,
            avatar=target.avatar if target else None,
            description=target.platform if target else None,
        )
