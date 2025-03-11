from collections import defaultdict
from dataclasses import dataclass

from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_saa.utils.exceptions import NoBotFound

from nonebot_bison.config import config
from nonebot_bison.metrics import render_time_histogram, request_counter, request_time_histogram, sent_counter
from nonebot_bison.platform import platform_manager
from nonebot_bison.send import send_msgs
from nonebot_bison.types import SubUnit, Target
from nonebot_bison.utils import ClientManager, ProcessContext, Site
from nonebot_bison.utils.site import SkipRequestException


@dataclass
class Schedulable:
    platform_name: str
    target: Target
    current_weight: int
    use_batch: bool = False


class Scheduler:
    schedulable_list: list[Schedulable]  # for load weigth from db
    batch_api_target_cache: dict[str, dict[Target, list[Target]]]  # platform_name -> (target -> [target])
    batch_platform_name_targets_cache: dict[str, list[Target]]
    client_mgr: ClientManager

    def __init__(
        self,
        scheduler_config: type[Site],
        schedulables: list[tuple[str, Target, bool]],  # [(platform_name, target, use_batch)]
        platform_name_list: list[str],
    ):
        self.name = scheduler_config.name
        if not scheduler_config:
            logger.error(f"scheduler config [{self.name}] not found, exiting")
            raise RuntimeError(f"{self.name} not found")
        self.scheduler_config = scheduler_config
        self.client_mgr = scheduler_config.client_mgr()
        self.scheduler_config_obj = self.scheduler_config()

        self.schedulable_list = []
        self.batch_platform_name_targets_cache = defaultdict(list)
        for platform_name, target, use_batch in schedulables:
            if use_batch:
                self.batch_platform_name_targets_cache[platform_name].append(target)
            self.schedulable_list.append(
                Schedulable(platform_name=platform_name, target=target, current_weight=0, use_batch=use_batch)
            )
        self._refresh_batch_api_target_cache()

        self.platform_name_list = platform_name_list
        self.pre_weight_val = 0  # 轮调度中“本轮”增加权重和的初值
        logger.info(
            f"register scheduler for {self.name} with "
            f"{self.scheduler_config.schedule_type} {self.scheduler_config.schedule_setting}"
        )
        scheduler.add_job(
            self.exec_fetch,
            self.scheduler_config.schedule_type,
            **self.scheduler_config.schedule_setting,
        )

    def _refresh_batch_api_target_cache(self):
        self.batch_api_target_cache = defaultdict(dict)
        for platform_name, targets in self.batch_platform_name_targets_cache.items():
            for target in targets:
                self.batch_api_target_cache[platform_name][target] = targets

    async def get_next_schedulable(self) -> Schedulable | None:
        if not self.schedulable_list:
            return None
        cur_weight = await config.get_current_weight_val(self.platform_name_list)
        weight_sum = self.pre_weight_val
        self.pre_weight_val = 0
        cur_max_schedulable = None
        for schedulable in self.schedulable_list:
            schedulable.current_weight += cur_weight[f"{schedulable.platform_name}-{schedulable.target}"]
            weight_sum += cur_weight[f"{schedulable.platform_name}-{schedulable.target}"]
            if not cur_max_schedulable or cur_max_schedulable.current_weight < schedulable.current_weight:
                cur_max_schedulable = schedulable
        assert cur_max_schedulable
        cur_max_schedulable.current_weight -= weight_sum
        return cur_max_schedulable

    async def exec_fetch(self):
        if not (schedulable := await self.get_next_schedulable()):
            return
        logger.trace(f"scheduler {self.name} fetching next target: [{schedulable.platform_name}]{schedulable.target}")

        context = ProcessContext(self.client_mgr)

        success_flag = False
        platform_obj = platform_manager[schedulable.platform_name](context)
        try:
            with request_time_histogram.labels(
                platform_name=schedulable.platform_name, site_name=platform_obj.site.name
            ).time():
                if schedulable.use_batch:
                    batch_targets = self.batch_api_target_cache[schedulable.platform_name][schedulable.target]
                    sub_units = []
                    for batch_target in batch_targets:
                        userinfo = await config.get_platform_target_subscribers(schedulable.platform_name, batch_target)
                        sub_units.append(SubUnit(batch_target, userinfo))
                    to_send = await platform_obj.do_batch_fetch_new_post(sub_units)
                else:
                    send_userinfo_list = await config.get_platform_target_subscribers(
                        schedulable.platform_name, schedulable.target
                    )
                    to_send = await platform_obj.do_fetch_new_post(SubUnit(schedulable.target, send_userinfo_list))
                success_flag = True
        except SkipRequestException as err:
            logger.debug(f"skip request: {err}")
        except Exception as err:
            records = context.gen_req_records()
            for record in records:
                logger.warning("API request record: " + record)
            err.args += (records,)
            raise

        request_counter.labels(
            platform_name=schedulable.platform_name,
            site_name=platform_obj.site.name,
            target=schedulable.target,
            success=success_flag,
        ).inc()
        if not to_send:
            return
        sent_counter.labels(
            platform_name=schedulable.platform_name, site_name=platform_obj.site.name, target=schedulable.target
        ).inc()
        with render_time_histogram.labels(
            platform_name=schedulable.platform_name, site_name=platform_obj.site.name
        ).time():
            for user, send_list in to_send:
                for send_post in send_list:
                    logger.info(f"send to {user}: {send_post}")
                    try:
                        await send_msgs(
                            user,
                            await send_post.generate_messages(),
                        )
                    except NoBotFound:
                        logger.warning("no bot connected")

    def insert_new_schedulable(self, platform_name: str, target: Target):
        self.pre_weight_val += 1000
        new_schedulable = Schedulable(platform_name, target, 1000, platform_manager[platform_name].use_batch)

        if new_schedulable.use_batch:
            self.batch_platform_name_targets_cache[platform_name].append(target)
            self._refresh_batch_api_target_cache()

        self.schedulable_list.append(new_schedulable)
        logger.info(f"insert [{platform_name}]{target} to Schduler({self.scheduler_config.name})")

    def delete_schedulable(self, platform_name, target: Target):
        if platform_manager[platform_name].use_batch:
            self.batch_platform_name_targets_cache[platform_name].remove(target)
            self._refresh_batch_api_target_cache()

        if not self.schedulable_list:
            return
        to_find_idx = None
        for idx, schedulable in enumerate(self.schedulable_list):
            if schedulable.platform_name == platform_name and schedulable.target == target:
                to_find_idx = idx
                break
        if to_find_idx is not None:
            deleted_schdulable = self.schedulable_list.pop(to_find_idx)
            self.pre_weight_val -= deleted_schdulable.current_weight
