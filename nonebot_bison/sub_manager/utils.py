import contextlib
from itertools import groupby
from operator import attrgetter
from typing import Annotated

from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot.params import Depends, EventPlainText, EventToMe
from nonebot.permission import SUPERUSER
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot_plugin_saa import PlatformTarget, extract_target

from nonebot_bison.config import config
from nonebot_bison.platform import platform_manager
from nonebot_bison.plugin_config import plugin_config
from nonebot_bison.types import Category
from nonebot_bison.types import Target as T_Target
from nonebot_bison.utils.site import is_cookie_client_manager


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
    matcher: type[Matcher],
    state: T_State,
    user_info: PlatformTarget | None = None,
    is_index=False,
    is_show_cookie=False,
    is_hide_no_cookie_platfrom=False,
):
    """根据配置参数，生产订阅列表文本，同时将订阅信息存入state["sub_table"]"""
    if user_info:
        sub_list = await config.list_subscribe(user_info)
    else:
        sub_list = await config.list_subs_with_all_info()
        sub_list = [
            next(group)
            for key, group in groupby(sorted(sub_list, key=attrgetter("target_id")), key=attrgetter("target_id"))
        ]
    if is_hide_no_cookie_platfrom:
        sub_list = [
            sub
            for sub in sub_list
            if is_cookie_client_manager(platform_manager[sub.target.platform_name].site.client_mgr)
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
                    target=T_Target(sub.target.target), site_name=platform.site.name, is_anonymous=False
                )
                if target_cookies:
                    res += "  关联的 Cookie：\n"
                    for cookie in target_cookies:
                        res += f"  \t{cookie.cookie_name}\n"

        else:
            res += f" （平台 {sub.target.platform_name} 已失效，请删除此订阅）"

    return res


async def only_allow_private(
    event: Event,
    matcher: type[Matcher],
):
    if not (hasattr(event, "message_type") and getattr(event, "message_type") == "private"):
        await matcher.finish("请在私聊中使用此命令")
