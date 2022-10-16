import nonebot
from nonebot.adapters.onebot.v11.bot import Bot

from ..apis import check_sub_target
from ..config import (
    NoSuchSubscribeException,
    NoSuchTargetException,
    NoSuchUserException,
    config,
)
from ..config.db_config import SubscribeDupException
from ..platform import platform_manager
from ..types import Target as T_Target
from ..types import WeightConfig
from .jwt import pack_jwt
from .token_manager import token_manager


async def test():
    return {"status": 200, "text": "test"}


async def get_global_conf():
    res = {}
    for platform_name, platform in platform_manager.items():
        res[platform_name] = {
            "platformName": platform_name,
            "categories": platform.categories,
            "enabledTag": platform.enable_tag,
            "name": platform.name,
            "hasTarget": getattr(platform, "has_target"),
        }
    return {"platformConf": res}


async def get_admin_groups(qq: int):
    bot = nonebot.get_bot()
    groups = await bot.call_api("get_group_list")
    res = []
    for group in groups:
        group_id = group["group_id"]
        users = await bot.call_api("get_group_member_list", group_id=group_id)
        for user in users:
            if user["user_id"] == qq and user["role"] in ("owner", "admin"):
                res.append({"id": group_id, "name": group["group_name"]})
    return res


async def auth(token: str):
    if qq_tuple := token_manager.get_user(token):
        qq, nickname = qq_tuple
        bot = nonebot.get_bot()
        assert isinstance(bot, Bot)
        groups = await bot.call_api("get_group_list")
        if str(qq) in nonebot.get_driver().config.superusers:
            jwt_obj = {
                "id": qq,
                "type": "admin",
                "groups": list(
                    map(
                        lambda info: {
                            "id": info["group_id"],
                            "name": info["group_name"],
                        },
                        groups,
                    )
                ),
            }
            ret_obj = {
                "type": "admin",
                "name": nickname,
                "id": qq,
                "token": pack_jwt(jwt_obj),
            }
            return {"status": 200, **ret_obj}
        if admin_groups := await get_admin_groups(int(qq)):
            jwt_obj = {"id": str(qq), "type": "user", "groups": admin_groups}
            ret_obj = {
                "type": "user",
                "name": nickname,
                "id": qq,
                "token": pack_jwt(jwt_obj),
            }
            return {"status": 200, **ret_obj}
        else:
            return {"status": 400, "type": "", "name": "", "id": 0, "token": ""}
    else:
        return {"status": 400, "type": "", "name": "", "id": 0, "token": ""}


async def get_subs_info(jwt_obj: dict):
    groups = jwt_obj["groups"]
    res = {}
    for group in groups:
        group_id = group["id"]
        raw_subs = await config.list_subscribe(group_id, "group")
        subs = list(
            map(
                lambda sub: {
                    "platformName": sub.target.platform_name,
                    "targetName": sub.target.target_name,
                    "cats": sub.categories,
                    "tags": sub.tags,
                    "target": sub.target.target,
                },
                raw_subs,
            )
        )
        res[group_id] = {"name": group["name"], "subscribes": subs}
    return res


async def get_target_name(platform_name: str, target: str, jwt_obj: dict):
    return {"targetName": await check_sub_target(platform_name, target)}


async def add_group_sub(
    group_number: int,
    platform_name: str,
    target: str,
    target_name: str,
    cats: list[int],
    tags: list[str],
):
    try:
        await config.add_subscribe(
            int(group_number),
            "group",
            T_Target(target),
            target_name,
            platform_name,
            cats,
            tags,
        )
        return {"status": 200, "msg": ""}
    except SubscribeDupException:
        return {"status": 403, "msg": ""}


async def del_group_sub(group_number: int, platform_name: str, target: str):
    try:
        await config.del_subscribe(int(group_number), "group", target, platform_name)
    except (NoSuchUserException, NoSuchSubscribeException):
        return {"status": 400, "msg": "删除错误"}
    return {"status": 200, "msg": ""}


async def update_group_sub(
    group_number: int,
    platform_name: str,
    target: str,
    target_name: str,
    cats: list[int],
    tags: list[str],
):
    try:
        await config.update_subscribe(
            int(group_number), "group", target, target_name, platform_name, cats, tags
        )
    except (NoSuchUserException, NoSuchSubscribeException):
        return {"status": 400, "msg": "更新错误"}
    return {"status": 200, "msg": ""}


async def get_weight_config():
    return await config.get_all_weight_config()


async def update_weigth_config(
    platform_name: str, target: str, weight_config: WeightConfig
):
    try:
        await config.update_time_weight_config(
            T_Target(target), platform_name, weight_config
        )
    except NoSuchTargetException:
        return {"status": 400, "msg": "该订阅不存在"}
    return {"status": 200, "msg": ""}
