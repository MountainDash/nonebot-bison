from typing import cast

from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText
from nonebot.adapters import Message, MessageTemplate

from ..platform import platform_manager
from .utils import common_platform, gen_handle_cancel
from ..utils.site import CookieClientManager, is_cookie_client_manager


def do_add_cookie(add_cookie: type[Matcher]):
    handle_cancel = gen_handle_cancel(add_cookie, "已中止添加cookie")

    @add_cookie.handle()
    async def init_promote(state: T_State):
        state["_prompt"] = (
            "请输入想要添加 Cookie 的平台，目前支持，请输入冒号左边的名称：\n"
            + "".join(
                [
                    f"{platform_name}: {platform_manager[platform_name].name}\n"
                    for platform_name in common_platform
                    if is_cookie_client_manager(platform_manager[platform_name].site.client_mgr)
                ]
            )
            + "要查看全部平台请输入：“全部”\n中止添加cookie过程请输入：“取消”"
        )

    @add_cookie.got("platform", MessageTemplate("{_prompt}"), [handle_cancel])
    async def parse_platform(state: T_State, platform: str = ArgPlainText()) -> None:
        if platform == "全部":
            message = "全部平台\n" + "\n".join(
                [
                    f"{platform_name}: {platform.name}"
                    for platform_name, platform in platform_manager.items()
                    if is_cookie_client_manager(platform_manager[platform_name].site.client_mgr)
                ]
            )
            await add_cookie.reject(message)
        elif platform == "取消":
            await add_cookie.finish("已中止添加cookie")
        elif platform in platform_manager:
            state["platform"] = platform
            state["site"] = platform_manager[platform].site
        else:
            await add_cookie.reject("平台输入错误")

    @add_cookie.handle()
    async def prepare_get_id(state: T_State):
        state["_prompt"] = "请输入 Cookie"

    @add_cookie.got("cookie", MessageTemplate("{_prompt}"), [handle_cancel])
    async def got_cookie(state: T_State, cookie: Message = Arg()):
        client_mgr: type[CookieClientManager] = cast(
            type[CookieClientManager], platform_manager[state["platform"]].site.client_mgr
        )
        cookie_text = cookie.extract_plain_text()
        if not await client_mgr.validate_cookie(cookie_text):
            await add_cookie.reject(state["site"].cookie_format_prompt)
        state["cookie"] = cookie_text

    @add_cookie.handle()
    async def add_cookie_process(state: T_State):
        client_mgr = cast(CookieClientManager, platform_manager[state["platform"]].site.client_mgr)
        await client_mgr.add_user_cookie(state["cookie"])
        await add_cookie.finish(
            f"已添加 Cookie: {state['cookie']} 到平台 {state['platform']}" + "\n请使用“关联cookie”为 Cookie 关联订阅"
        )
