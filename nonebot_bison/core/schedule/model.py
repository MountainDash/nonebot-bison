from typing import NamedTuple

from nonebot_plugin_saa import PlatformTarget as SendTarget

from nonebot_bison.typing import Category, Tag, Target


class UserSubInfo(NamedTuple):
    user: SendTarget
    categories: list[Category]
    tags: list[Tag]


class SubUnit(NamedTuple):
    sub_target: Target
    user_sub_infos: list[UserSubInfo]


type SubUnits = SubUnit | list[SubUnit]
