from .types import Target
from .scheduler import scheduler_dict
from .platform import platform_manager


async def check_sub_target(platform_name: str, target: Target):
    platform = platform_manager[platform_name]
    scheduler_conf_class = platform.scheduler
    scheduler = scheduler_dict[scheduler_conf_class]
    client = await scheduler.scheduler_config_obj.get_query_name_client()

    return await platform_manager[platform_name].get_target_name(client, target)
