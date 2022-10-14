from typing import Type

from ..config import config
from ..config.db_model import Target
from ..platform import platform_manager
from ..types import Target as T_Target
from ..utils import SchedulerConfig
from .scheduler import Scheduler

scheduler_dict: dict[Type[SchedulerConfig], Scheduler] = {}


async def init_scheduler():
    _schedule_class_dict: dict[Type[SchedulerConfig], list[Target]] = {}
    _schedule_class_platform_dict: dict[Type[SchedulerConfig], list[str]] = {}
    for platform in platform_manager.values():
        scheduler_config = platform.scheduler
        if not hasattr(scheduler_config, "name") or not scheduler_config.name:
            scheduler_config.name = f"AnonymousScheduleConfig[{platform.platform_name}]"

        platform_name = platform.platform_name
        targets = await config.get_platform_target(platform_name)
        if scheduler_config not in _schedule_class_dict:
            _schedule_class_dict[scheduler_config] = targets
        else:
            _schedule_class_dict[scheduler_config].extend(targets)
        if scheduler_config not in _schedule_class_platform_dict:
            _schedule_class_platform_dict[scheduler_config] = [platform_name]
        else:
            _schedule_class_platform_dict[scheduler_config].append(platform_name)
    for scheduler_config, target_list in _schedule_class_dict.items():
        schedulable_args = []
        for target in target_list:
            schedulable_args.append((target.platform_name, T_Target(target.target)))
        platform_name_list = _schedule_class_platform_dict[scheduler_config]
        scheduler_dict[scheduler_config] = Scheduler(
            scheduler_config, schedulable_args, platform_name_list
        )


async def handle_insert_new_target(platform_name: str, target: T_Target):
    platform = platform_manager[platform_name]
    scheduler_obj = scheduler_dict[platform.scheduler]
    scheduler_obj.insert_new_schedulable(platform_name, target)


async def handle_delete_target(platform_name: str, target: T_Target):
    platform = platform_manager[platform_name]
    scheduler_obj = scheduler_dict[platform.scheduler]
    scheduler_obj.delete_schedulable(platform_name, target)


config.register_add_target_hook(handle_insert_new_target)
config.register_delete_target_hook(handle_delete_target)
