from typing import Literal, NamedTuple, TypeVar

from pydantic import BaseModel


class CeobeTextPic(NamedTuple):
    text: str
    pics: list[bytes | str]


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
    type: str | None = None
    """类型"""
    is_long_text: bool | None = None
    """是否长文"""
    is_retweeted: bool = False
    """是否转发"""
    retweeted: CeobeRetweeted | None = None
    """展示类型，公告类型的数据源有这个字段"""
    display_type: int | None = None

    class Config:
        extra = "allow"


class CeobeSource(BaseModel):
    data: str
    """数据源id"""
    type: str
    """数据源类型"""


class CeobeTimestamp(BaseModel):
    fetcher: int
    """蹲饼时间，毫秒"""
    platform_precision: Literal["none", "day", "hour", "minute", "second", "ms"]
    """平台时间精度，不足的长度补0"""
    platform: int | None = None
    """平台时间戳，毫秒"""


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


ResponseModel = TypeVar("ResponseModel", bound=CookiesResponse | CombIdResponse | CookieIdResponse | DataSourceResponse)
