from .types import Target
from .config.db_model import Cookie
from .scheduler import scheduler_dict
from .platform import platform_manager


async def check_sub_target(platform_name: str, target: Target):
    platform = platform_manager[platform_name]
    scheduler_conf_class = platform.site
    scheduler = scheduler_dict[scheduler_conf_class]
    client = await scheduler.client_mgr.get_query_name_client()

    return await platform_manager[platform_name].get_target_name(client, target)


async def check_sub_target_cookie(platform_name: str, target: Target, cookie: str):
    # TODO
    return "check pass"


async def get_cookie_friendly_name(cookie: Cookie):
    # TODO
    return cookie.platform_name + cookie.content[:10]
