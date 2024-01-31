from dataclasses import dataclass
from typing import Any, Literal, NewType, NamedTuple

from nonebot_plugin_saa import PlatformTarget

RawPost = Any
Target = NewType("Target", str)
Category = int
Tag = str


@dataclass(eq=True, frozen=True)
class User:
    user: int
    user_type: Literal["group", "private"]


class UserSubInfo(NamedTuple):
    user: PlatformTarget
    categories: list[Category]
    tags: list[Tag]
