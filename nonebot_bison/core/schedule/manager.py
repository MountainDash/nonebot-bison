from dataclasses import dataclass, field
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

type SiteName = str


@dataclass
class SchedulerDict:
    schedulers: dict[SiteName, Scheduler] = field(default_factory=dict)

    def __getitem__(self, key: str | SiteConfig, /) -> Scheduler:
        match key:
            case str():
                return self.schedulers[key]
            case SiteConfig():
                return self.schedulers[key.name]
            case _:
                raise TypeError(f"Unsupport SchedulerDict key type: {type(key)}")

    def __setitem__(self, key: str | SiteConfig, value: Scheduler, /):
        match key:
            case str():
                self.schedulers[key] = value
            case SiteConfig():
                self.schedulers[key.name] = value
            case _:
                raise TypeError(f"Unsupport SchedulerDict key type: {type(key)}")

    def __contains__(self, key: str | SiteConfig) -> bool:
        match key:
            case str():
                return key in self.schedulers
            case SiteConfig():
                return key.name in self.schedulers
            case _:
                raise TypeError(f"Unsupport SchedulerDict key type: {type(key)}")


scheduler_dict = SchedulerDict()


async def init_scheduler():
    _schedule_class_name: dict[SiteName, SiteConfig] = {}
    _schedule_class_dict: dict[SiteName, list[Target]] = {}
    _schedule_class_platform_dict: dict[SiteName, list[str]] = {}
    for platform in Platform.registry.values():
        platform: Platform = platform
        site = platform.site_config
        if not hasattr(site, "name") or not site.name:
            site.name = f"AnonymousScheduleConfig[{platform.platform_config.display_name}]"

        site_name = site.name
        platform_name = platform.platform_config.display_name
        targets = await data_access.get_platform_target(platform_name)
        if site_name not in _schedule_class_dict:
            _schedule_class_name[site_name] = site
            _schedule_class_dict[site_name] = list(targets)
        else:
            _schedule_class_dict[site_name].extend(targets)
        if site_name not in _schedule_class_platform_dict:
            _schedule_class_platform_dict[site_name] = [platform_name]
        else:
            _schedule_class_platform_dict[site_name].append(platform_name)

    for site, target_list in _schedule_class_dict.items():
        if not plugin_config.bison_use_browser and _schedule_class_name[site].require_browser:
            logger.warning(f"{site} requires browser, it will not schedule.")
            continue

        schedulable_args = []
        for target in target_list:
            schedulable_args.append(
                (target.platform_name, T_Target(target.target), Platform.registry[target.platform_name].use_batch)
            )
        platform_name_list = _schedule_class_platform_dict[site]
        scheduler_dict[site] = Scheduler(_schedule_class_name[site], schedulable_args, platform_name_list)
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
