import contextlib
from typing import Annotated
from itertools import groupby
from operator import attrgetter

from nonebot.rule import Rule
from nonebot.adapters import Event
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.params import Depends, EventToMe, EventPlainText
from nonebot_plugin_saa import PlatformTarget, extract_target

from ..config import config
from ..types import Category
from ..platform import platform_manager
from ..plugin_config import plugin_config
from ..apis import get_cookie_friendly_name


def _configurable_to_me(to_me: bool = EventToMe()):
    if plugin_config.bison_to_me:
        return to_me
    else:
        return True


configurable_to_me = Rule(_configurable_to_me)

common_platform = [
    p.platform_name
    for p in filter(
        lambda platform: platform.enabled and platform.is_common,
        platform_manager.values(),
    )
]


def gen_handle_cancel(matcher: type[Matcher], message: str):
    async def _handle_cancel(text: Annotated[str, EventPlainText()]):
        if text == "取消":
            await matcher.finish(message)

    return Depends(_handle_cancel)


def ensure_user_info(matcher: type[Matcher]):
    async def _check_user_info(state: T_State):
        if not state.get("target_user_info"):
            await matcher.finish("No target_user_info set, this shouldn't happen, please issue")

    return _check_user_info


async def set_target_user_info(event: Event, state: T_State):
    user = extract_target(event)
    state["target_user_info"] = user


def admin_permission():
    permission = SUPERUSER
    with contextlib.suppress(ImportError):
        from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

        permission = permission | GROUP_ADMIN | GROUP_OWNER

    return permission


async def generate_sub_list_text(
    matcher: type[Matcher], state: T_State, user_info: PlatformTarget = None, is_index=False, is_show_cookie=False
):
    if user_info:
        sub_list = await config.list_subscribe(user_info)
    else:
        sub_list = await config.list_subs_with_all_info()
        sub_list = [
            next(group)
            for key, group in groupby(sorted(sub_list, key=attrgetter("target_id")), key=attrgetter("target_id"))
        ]
    if not sub_list:
        await matcher.finish("暂无已订阅账号\n请使用“添加订阅”命令添加订阅")
    res = "订阅的帐号为：\n"
    state["sub_table"] = {}
    for index, sub in enumerate(sub_list, 1):
        state["sub_table"][index] = {
            "platform_name": sub.target.platform_name,
            "target": sub.target.target,
        }
        res += f"{index} " if is_index else ""
        res += f"{sub.target.platform_name} {sub.target.target_name} {sub.target.target}\n"
        if platform := platform_manager.get(sub.target.platform_name):
            if platform.categories:
                res += " [{}]".format(", ".join(platform.categories[Category(x)] for x in sub.categories)) + "\n"
            if platform.enable_tag:
                if sub.tags:
                    res += " {}".format(", ".join(sub.tags)) + "\n"
            if is_show_cookie:
                target_cookies = await config.get_cookie(
                    target=sub.target.target, platform_name=sub.target.platform_name
                )
                if target_cookies:
                    res += "  关联的 Cookie：\n"
                    for cookie in target_cookies:
                        res += f"  \t{await get_cookie_friendly_name(cookie)}\n"

        else:
            res += f" （平台 {sub.target.platform_name} 已失效，请删除此订阅）"

    return res
