from datetime import time
from typing import NamedTuple

from pydantic import BaseModel

from .subscribe import Target, UserSubInfo


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


class SubUnit(NamedTuple):
    sub_target: Target
    user_sub_infos: list[UserSubInfo]
