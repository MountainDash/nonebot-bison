from pydantic import BaseModel


class PlatformConfig(BaseModel):
    name: str
    categories: dict[int, str]
    enabledTag: bool
    platformName: str
    siteName: str
    hasTarget: bool


class SiteConfig(BaseModel):
    name: str
    enable_cookie: bool


AllPlatformConf = dict[str, PlatformConfig]
AllSiteConf = dict[str, SiteConfig]


class GlobalConf(BaseModel):
    platformConf: AllPlatformConf
    siteConf: AllSiteConf


class TokenResp(BaseModel):
    token: str
    type: str
    id: int
    name: str


class SubscribeConfig(BaseModel):
    platformName: str
    target: str
    targetName: str
    cats: list[int]
    tags: list[str]


class SubscribeGroupDetail(BaseModel):
    name: str
    subscribes: list[SubscribeConfig]


SubscribeResp = dict[int, SubscribeGroupDetail]


class AddSubscribeReq(BaseModel):
    platformName: str
    target: str
    targetName: str
    cats: list[int]
    tags: list[str]


class StatusResp(BaseModel):
    ok: bool
    msg: str


from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Target(BaseModel):
    platform_name: str
    target_name: str
    target: str


class Cookie(BaseModel):
    id: int
    site_name: str
    content: str
    cookie_name: str
    last_usage: datetime
    status: str
    cd_milliseconds: int
    is_universal: bool
    is_anonymous: bool
    tags: dict[str, Any]


class CookieTarget(BaseModel):
    target: Target
    cookie_id: int
