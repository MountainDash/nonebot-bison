from abc import ABC

from pydantic import BaseModel
from nonebot_plugin_saa.utils import AllSupportedPlatformTarget as UserInfo

from ....types import Tag, Category


class NBESFBase(BaseModel, ABC):
    version: int  # 表示nbesf格式版本，有效版本从1开始
    groups: list = []

    class Config:
        orm_mode = True


class SubReceipt(BaseModel):
    """
    快递包中每件货物的收据

    导入订阅时的Model
    """

    user: UserInfo
    target: str
    target_name: str
    platform_name: str
    cats: list[Category]
    tags: list[Tag]
    # default_schedule_weight: int
