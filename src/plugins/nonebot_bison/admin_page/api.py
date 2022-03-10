import nonebot
from nonebot.adapters.onebot.v11.bot import Bot

from ..config import Config, NoSuchSubscribeException, NoSuchUserException
from ..platform import check_sub_target, platform_manager
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
                "id": str(qq),
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
                "id": str(qq),
                "token": pack_jwt(jwt_obj),
            }
            return {"status": 200, **ret_obj}
        if admin_groups := await get_admin_groups(int(qq)):
            jwt_obj = {"id": str(qq), "groups": admin_groups}
            ret_obj = {
                "type": "user",
                "name": nickname,
                "id": str(qq),
                "token": pack_jwt(jwt_obj),
            }
            return {"status": 200, **ret_obj}
        else:
            return {"status": 400, "type": "", "name": "", "id": "", "token": ""}
    else:
        return {"status": 400, "type": "", "name": "", "id": "", "token": ""}


async def get_subs_info(jwt_obj: dict):
    groups = jwt_obj["groups"]
    res = {}
    for group in groups:
        group_id = group["id"]
        config = Config()
        subs = list(
            map(
                lambda sub: {
                    "platformName": sub["target_type"],
                    "target": sub["target"],
                    "targetName": sub["target_name"],
                    "cats": sub["cats"],
                    "tags": sub["tags"],
                },
                config.list_subscribe(group_id, "group"),
            )
        )
        res[group_id] = {"name": group["name"], "subscribes": subs}
    return res


async def get_target_name(platform_name: str, target: str, jwt_obj: dict):
    return {"targetName": await check_sub_target(platform_name, target)}


async def add_group_sub(
    group_number: str,
    platform_name: str,
    target: str,
    target_name: str,
    cats: list[int],
    tags: list[str],
):
    config = Config()
    config.add_subscribe(
        int(group_number), "group", target, target_name, platform_name, cats, tags
    )
    return {"status": 200, "msg": ""}


async def del_group_sub(group_number: str, platform_name: str, target: str):
    config = Config()
    try:
        config.del_subscribe(int(group_number), "group", target, platform_name)
    except (NoSuchUserException, NoSuchSubscribeException):
        return {"status": 400, "msg": "删除错误"}
    return {"status": 200, "msg": ""}


async def update_group_sub(
    group_number: str,
    platform_name: str,
    target: str,
    target_name: str,
    cats: list[int],
    tags: list[str],
):
    config = Config()
    try:
        config.update_subscribe(
            int(group_number), "group", target, target_name, platform_name, cats, tags
        )
    except (NoSuchUserException, NoSuchSubscribeException):
        return {"status": 400, "msg": "更新错误"}
    return {"status": 200, "msg": ""}
