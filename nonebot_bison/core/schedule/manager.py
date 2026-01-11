from typing import TYPE_CHECKING

from nonebot.log import logger

from nonebot_bison.core.platform import Platform
from nonebot_bison.core.site import SiteConfig
from nonebot_bison.db import data_access
from nonebot_bison.setting import plugin_config
from nonebot_bison.typing import Target as T_Target

from .scheduler import Scheduler

if TYPE_CHECKING:
    from nonebot_bison.db.db_model import Target

scheduler_dict: dict[SiteConfig, Scheduler] = {}


async def init_scheduler():
    _schedule_class_dict: dict[SiteConfig, list[Target]] = {}
    _schedule_class_platform_dict: dict[SiteConfig, list[str]] = {}
    for platform in Platform.registry.values():
        platform: Platform = platform
        site = platform.site_config
        if not hasattr(site, "name") or not site.name:
            site.name = f"AnonymousScheduleConfig[{platform.platform_config.display_name}]"

        platform_name = platform.platform_config.display_name
        targets = await data_access.get_platform_target(platform_name)
        if site not in _schedule_class_dict:
            _schedule_class_dict[site] = list(targets)
        else:
            _schedule_class_dict[site].extend(targets)
        if site not in _schedule_class_platform_dict:
            _schedule_class_platform_dict[site] = [platform_name]
        else:
            _schedule_class_platform_dict[site].append(platform_name)
    for site, target_list in _schedule_class_dict.items():
        if not plugin_config.bison_use_browser and site.require_browser:
            logger.warning(f"{site.name} requires browser, it will not schedule.")
            continue

        schedulable_args = []
        for target in target_list:
            schedulable_args.append(
                (target.platform_name, T_Target(target.target), Platform.registry[target.platform_name].use_batch)
            )
        platform_name_list = _schedule_class_platform_dict[site]
        scheduler_dict[site] = Scheduler(site, schedulable_args, platform_name_list)
        # if is_cookie_client_manager(site.client_mgr):
        #     client_mgr = cast("CookieClientManager", scheduler_dict[site].client_mgr)
        #     await client_mgr.refresh_client()
        # FIXME: 记得实现 CookieClientManager 的 on_init_scheduler 方法
        await scheduler_dict[site].client_mgr.on_init_scheduler()
    data_access.register_add_target_hook(handle_insert_new_target)
    data_access.register_delete_target_hook(handle_delete_target)


async def handle_insert_new_target(platform_name: str, target: T_Target):
    platform = Platform.registry[platform_name]
    scheduler_obj = scheduler_dict[platform.site]
    scheduler_obj.insert_new_schedulable(platform_name, target)


async def handle_delete_target(platform_name: str, target: T_Target):
    if platform_name not in Platform.registry:
        return
    platform: Platform = Platform.registry[platform_name]
    scheduler_obj = scheduler_dict[platform.site_config]
    scheduler_obj.delete_schedulable(platform_name, target)
