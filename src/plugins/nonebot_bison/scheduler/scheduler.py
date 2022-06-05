from dataclasses import dataclass
from typing import Optional

from nonebot.log import logger

from ..config import config
from ..platform.platform import Platform
from ..types import Target
from ..utils import SchedulerConfig


@dataclass
class Schedulable:
    platform_name: str
    target: Target
    current_weight: int


class Scheduler:

    schedulable_list: list[Schedulable]

    def __init__(self, name: str, schedulables: list[tuple[str, Target]]):
        conf = SchedulerConfig.registry.get(name)
        if not conf:
            logger.error(f"scheduler config [{name}] not found, exiting")
            raise RuntimeError(f"{name} not found")
        self.scheduler_config = conf
        self.schedulable_list = []
        platform_name_set = set()
        for platform_name, target in schedulables:
            self.schedulable_list.append(
                Schedulable(
                    platform_name=platform_name, target=target, current_weight=0
                )
            )
            platform_name_set.add(platform_name)
        self.platform_name_list = list(platform_name_set)
        self.pre_weight_val = 0  # 轮调度中“本轮”增加权重和的初值

    async def schedule(self) -> Optional[Schedulable]:
        if not self.schedulable_list:
            return None
        cur_weight = await config.get_current_weight_val(self.platform_name_list)
        weight_sum = self.pre_weight_val
        self.pre_weight_val = 0
        cur_max_schedulable = None
        for schedulable in self.schedulable_list:
            schedulable.current_weight += cur_weight[
                f"{schedulable.platform_name}-{schedulable.target}"
            ]
            weight_sum += cur_weight[
                f"{schedulable.platform_name}-{schedulable.target}"
            ]
            if (
                not cur_max_schedulable
                or cur_max_schedulable.current_weight < schedulable.current_weight
            ):
                cur_max_schedulable = schedulable
        assert cur_max_schedulable
        cur_max_schedulable.current_weight -= weight_sum
        return cur_max_schedulable

    def insert_new_schedulable(self, platform_name: str, target: Target):
        self.pre_weight_val += 1000
        self.schedulable_list.append(Schedulable(platform_name, target, 1000))
        logger.info(
            f"insert [{platform_name}]{target} to Schduler({self.scheduler_config.name})"
        )

    def delete_schedulable(self, platform_name, target: Target):
        if not self.schedulable_list:
            return
        to_find_idx = None
        for idx, schedulable in enumerate(self.schedulable_list):
            if (
                schedulable.platform_name == platform_name
                and schedulable.target == target
            ):
                to_find_idx = idx
                break
        if to_find_idx is not None:
            deleted_schdulable = self.schedulable_list.pop(to_find_idx)
            self.pre_weight_val -= deleted_schdulable.current_weight
        return
