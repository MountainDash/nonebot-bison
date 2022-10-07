from nonebot.log import logger

from ..config import config
from ..config.db_model import Target
from ..platform import platform_manager
from ..types import Target as T_Target
from ..utils import SchedulerConfig
from .scheduler import Scheduler

scheduler_dict: dict[str, Scheduler] = {}


async def init_scheduler():
    _schedule_class_dict: dict[str, list[Target]] = {}
    _schedule_class_platform_dict: dict[str, list[str]] = {}
    for platform in platform_manager.values():
        scheduler_class = platform.scheduler_class
        platform_name = platform.platform_name
        targets = await config.get_platform_target(platform_name)
        if scheduler_class not in _schedule_class_dict:
            _schedule_class_dict[scheduler_class] = targets
        else:
            _schedule_class_dict[scheduler_class].extend(targets)
        if scheduler_class not in _schedule_class_platform_dict:
            _schedule_class_platform_dict[scheduler_class] = [platform_name]
        else:
            _schedule_class_platform_dict[scheduler_class].append(platform_name)
    for scheduler_class, target_list in _schedule_class_dict.items():
        schedulable_args = []
        for target in target_list:
            schedulable_args.append((target.platform_name, T_Target(target.target)))
        platform_name_list = _schedule_class_platform_dict[scheduler_class]
        scheduler_dict[scheduler_class] = Scheduler(
            scheduler_class, schedulable_args, platform_name_list
        )


async def handle_insert_new_target(platform_name: str, target: T_Target):
    platform = platform_manager[platform_name]
    scheduler_obj = scheduler_dict[platform.scheduler_class]
    scheduler_obj.insert_new_schedulable(platform_name, target)


async def handle_delete_target(platform_name: str, target: T_Target):
    platform = platform_manager[platform_name]
    scheduler_obj = scheduler_dict[platform.scheduler_class]
    scheduler_obj.delete_schedulable(platform_name, target)


config.register_add_target_hook(handle_insert_new_target)
config.register_delete_target_hook(handle_delete_target)
