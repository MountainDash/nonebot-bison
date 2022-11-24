from dataclasses import dataclass
from typing import Optional, Type

import nonebot
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.log import logger

from ..config import config
from ..platform import platform_manager
from ..send import send_msgs
from ..types import Target
from ..utils import ProcessContext, SchedulerConfig
from .aps import aps


@dataclass
class Schedulable:
    platform_name: str
    target: Target
    current_weight: int


class Scheduler:

    schedulable_list: list[Schedulable]

    def __init__(
        self,
        scheduler_config: Type[SchedulerConfig],
        schedulables: list[tuple[str, Target]],
        platform_name_list: list[str],
    ):
        self.name = scheduler_config.name
        if not scheduler_config:
            logger.error(f"scheduler config [{self.name}] not found, exiting")
            raise RuntimeError(f"{self.name} not found")
        self.scheduler_config = scheduler_config
        self.scheduler_config_obj = self.scheduler_config()
        self.schedulable_list = []
        for platform_name, target in schedulables:
            self.schedulable_list.append(
                Schedulable(
                    platform_name=platform_name, target=target, current_weight=0
                )
            )
        self.platform_name_list = platform_name_list
        self.pre_weight_val = 0  # 轮调度中“本轮”增加权重和的初值
        logger.info(
            f"register scheduler for {self.name} with {self.scheduler_config.schedule_type} {self.scheduler_config.schedule_setting}"
        )
        aps.add_job(
            self.exec_fetch,
            self.scheduler_config.schedule_type,
            **self.scheduler_config.schedule_setting,
        )

    async def get_next_schedulable(self) -> Optional[Schedulable]:
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

    async def exec_fetch(self):
        context = ProcessContext()
        if not (schedulable := await self.get_next_schedulable()):
            return
        logger.debug(
            f"scheduler {self.name} fetching next target: [{schedulable.platform_name}]{schedulable.target}"
        )
        send_userinfo_list = await config.get_platform_target_subscribers(
            schedulable.platform_name, schedulable.target
        )

        client = await self.scheduler_config_obj.get_client(schedulable.target)
        context.register_to_client(client)

        try:
            platform_obj = platform_manager[schedulable.platform_name](context, client)
            to_send = await platform_obj.do_fetch_new_post(
                schedulable.target, send_userinfo_list
            )
        except Exception as err:
            records = context.gen_req_records()
            for record in records:
                logger.warning("API request record: " + record)
            err.args += (records,)
            raise

        if not to_send:
            return
        bot = nonebot.get_bot()
        assert isinstance(bot, Bot)
        for user, send_list in to_send:
            for send_post in send_list:
                logger.info("send to {}: {}".format(user, send_post))
                if not bot:
                    logger.warning("no bot connected")
                else:
                    await send_msgs(
                        bot,
                        user.user,
                        user.user_type,
                        await send_post.generate_messages(),
                    )

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
