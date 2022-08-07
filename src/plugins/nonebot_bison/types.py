from dataclasses import dataclass
from datetime import time
from typing import Any, Callable, Literal, NamedTuple, NewType

RawPost = NewType("RawPost", Any)
Target = NewType("Target", str)
Category = int
Tag = str


@dataclass(eq=True, frozen=True)
class User:
    user: int
    user_type: Literal["group", "private"]


@dataclass(eq=True, frozen=True)
class PlatformTarget:
    target: str
    platform_name: str
    target_name: str


class UserSubInfo(NamedTuple):
    user: User
    categories: list[Category]
    tags: list[Tag]


@dataclass
class TimeWeightConfig:
    start_time: time
    end_time: time
    weight: int


@dataclass
class WeightConfig:

    default: int
    time_config: list[TimeWeightConfig]


@dataclass
class PlatformWeightConfigResp:
    target: Target
    target_name: str
    weight: WeightConfig
