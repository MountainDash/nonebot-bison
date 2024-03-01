from pydantic import BaseModel


class PlatformConfig(BaseModel):
    name: str
    categories: dict[int, str]
    enabledTag: bool
    platformName: str
    hasTarget: bool


AllPlatformConf = dict[str, PlatformConfig]


class GlobalConf(BaseModel):
    platformConf: AllPlatformConf


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
