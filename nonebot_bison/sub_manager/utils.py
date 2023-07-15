import contextlib
from typing import Annotated

from nonebot.rule import Rule
from nonebot.adapters import Event
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot_plugin_saa import extract_target
from nonebot.params import Depends, EventToMe, EventPlainText

from ..platform import platform_manager
from ..plugin_config import plugin_config


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
