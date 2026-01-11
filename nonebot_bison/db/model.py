from dataclasses import dataclass
from datetime import time
from typing import Literal

from pydantic import BaseModel

from nonebot_bison.typing import Target


@dataclass(eq=True, frozen=True)
class User:
    user: int
    user_type: Literal["group", "private"]


class TimeWeightConfig(BaseModel):
    start_time: time
    end_time: time
    weight: int


class WeightConfig(BaseModel):
    default: int
    time_config: list[TimeWeightConfig]


class PlatformWeightConfigResp(BaseModel):
    target: Target
    target_name: str
    platform_name: str
    weight: WeightConfig
