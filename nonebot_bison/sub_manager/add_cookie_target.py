from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText
from nonebot.internal.adapter import MessageTemplate
from nonebot_plugin_saa import MessageFactory, PlatformTarget

from ..config import config
from ..utils import parse_text
from ..apis import get_cookie_friendly_name
from .utils import ensure_user_info, gen_handle_cancel, generate_sub_list_text


def do_add_cookie_target(add_cookie_target_matcher: type[Matcher]):
    handle_cancel = gen_handle_cancel(add_cookie_target_matcher, "已中止关联 cookie")

    add_cookie_target_matcher.handle()(ensure_user_info(add_cookie_target_matcher))

    @add_cookie_target_matcher.handle()
    async def init_promote(state: T_State, user_info: PlatformTarget = Arg("target_user_info")):
        res = await generate_sub_list_text(
            add_cookie_target_matcher, state, user_info, is_index=True, is_show_cookie=True
        )
        res += "请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
        await MessageFactory(await parse_text(res)).send()

    @add_cookie_target_matcher.got("target_idx", parameterless=[handle_cancel])
    async def got_target_idx(state: T_State, target_idx: str = ArgPlainText()):
        try:
            target_idx = int(target_idx)
            state["target"] = state["sub_table"][target_idx]
        except Exception:
            await add_cookie_target_matcher.reject("序号错误")

    @add_cookie_target_matcher.handle()
    async def init_promote_cookie(state: T_State):

        cookies = await config.get_cookie(
            user=state["target_user_info"], platform_name=state["target"]["platform_name"]
        )
        associated_cookies = await config.get_cookie(
            user=state["target_user_info"],
            target=state["target"]["target"],
            platform_name=state["target"]["platform_name"],
        )
        associated_cookie_ids = {cookie.id for cookie in associated_cookies}
        cookies = [cookie for cookie in cookies if cookie.id not in associated_cookie_ids]
        if not cookies:
            await add_cookie_target_matcher.finish(
                "当前平台暂无可关联的 Cookie，请使用“添加cookie”命令添加或检查已关联的 Cookie"
            )
        state["cookies"] = cookies
        state["_prompt"] = "请选择一个 Cookie，已关联的 Cookie 不会显示\n" + "\n".join(
            [f"{idx}. {await get_cookie_friendly_name(cookie)}" for idx, cookie in enumerate(cookies, 1)]
        )

    @add_cookie_target_matcher.got("cookie_idx", MessageTemplate("{_prompt}"), [handle_cancel])
    async def got_cookie_idx(state: T_State, cookie_idx: str = ArgPlainText()):
        try:
            cookie_idx = int(cookie_idx)
            state["cookie"] = state["cookies"][cookie_idx - 1]
        except Exception:
            await add_cookie_target_matcher.reject("序号错误")

    @add_cookie_target_matcher.handle()
    async def add_cookie_target_process(state: T_State, user: PlatformTarget = Arg("target_user_info")):
        await config.add_cookie_target(state["target"]["target"], state["target"]["platform_name"], state["cookie"].id)
        await add_cookie_target_matcher.finish(
            f"已关联 Cookie: {await get_cookie_friendly_name(state['cookie'])} "
            f"到订阅 {state['target']['platform_name']} {state['target']['target']}"
        )
