from typing import NamedTuple, NewType

from nonebot_plugin_saa import PlatformTarget as SendTarget  # noqa: TC002

type Category = int
type Tag = str
Target = NewType("Target", str)


class UserSubInfo(NamedTuple):
    user: SendTarget
    categories: list[Category]
    tags: list[Tag]


class SubUnit(NamedTuple):
    sub_target: Target
    user_sub_infos: list[UserSubInfo]


type SubUnits = SubUnit | list[SubUnit]
