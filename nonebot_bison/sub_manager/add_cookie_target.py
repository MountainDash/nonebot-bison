from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.internal.adapter import MessageTemplate
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText
from nonebot.typing import T_State
from nonebot_plugin_saa import MessageFactory

from nonebot_bison.config import config
from nonebot_bison.platform import platform_manager
from nonebot_bison.utils import parse_text

from .utils import gen_handle_cancel, generate_platform_list_text, generate_sub_list_text, only_allow_private


def do_add_cookie_target(add_cookie_target_matcher: type[Matcher]):
    handle_cancel = gen_handle_cancel(add_cookie_target_matcher, "已中止关联 cookie")

    @add_cookie_target_matcher.handle()
    async def init_promote(state: T_State, event: MessageEvent):
        await only_allow_private(event, add_cookie_target_matcher)
        res = await generate_platform_list_text(add_cookie_target_matcher, state)
        await MessageFactory(await parse_text(res)).send()

    @add_cookie_target_matcher.got("platform_name", parameterless=[handle_cancel])
    async def got_platform_name(state: T_State, platform_name: str = ArgPlainText()):
        platform_name = platform_name.strip()
        if platform_name not in state["platform_table"]:
            await add_cookie_target_matcher.reject("平台名称错误，请输入支持的平台名称")
        state["selected_platform"] = platform_name

    @add_cookie_target_matcher.handle()
    async def init_promote_target(state: T_State):
        selected_platform = state["selected_platform"]
        res = await generate_sub_list_text(
            add_cookie_target_matcher,
            state,
            is_index=True,
            is_show_cookie=True,
            is_hide_no_cookie_platfrom=True,
            platform_filter=selected_platform,
            show_all_option=True,
        )
        res += "请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
        await MessageFactory(await parse_text(res)).send()

    @add_cookie_target_matcher.got("target_idx", parameterless=[handle_cancel])
    async def got_target_idx(state: T_State, target_idx: str = ArgPlainText()):
        try:
            target_idx = target_idx.strip()
            # 检查是否选择了"全部"选项
            # 计算"全部"选项的序号
            normal_keys = [k for k in state["sub_table"].keys() if k != "all"]
            all_option_index = str(len(normal_keys) + 1)
            if "all" in state["sub_table"] and target_idx == all_option_index:
                state["is_batch_mode"] = True
                state["batch_targets"] = state["sub_table"]["all"]["all_targets"]
                state["site"] = platform_manager[state["selected_platform"]].site
            else:
                state["is_batch_mode"] = False
                state["target"] = state["sub_table"][int(target_idx)]
                state["site"] = platform_manager[state["target"]["platform_name"]].site
        except Exception:
            await add_cookie_target_matcher.reject("序号错误")

    @add_cookie_target_matcher.handle()
    async def init_promote_cookie(state: T_State):
        # 获取 site 的所有实名 cookie，再排除掉已经关联的 cookie，剩下的就是可以关联的 cookie
        cookies = await config.get_cookie(site_name=state["site"].name, is_anonymous=False)

        if state.get("is_batch_mode", False):
            # 批量模式：排除所有已关联target的cookie
            all_associated_cookie_ids = set()
            for target_info in state["batch_targets"]:
                associated_cookies = await config.get_cookie(
                    target=target_info["target"],
                    site_name=state["site"].name,
                    is_anonymous=False,
                )
                all_associated_cookie_ids.update(cookie.id for cookie in associated_cookies)
            cookies = [cookie for cookie in cookies if cookie.id not in all_associated_cookie_ids]

            if not cookies:
                await add_cookie_target_matcher.finish(
                    '当前平台暂无可关联的 Cookie，请使用"添加cookie"命令添加或检查已关联的 Cookie'
                )

            target_count = len(state["batch_targets"])
            prompt_text = f"请选择一个 Cookie 关联到该平台的所有 {target_count} 个订阅，已关联的 Cookie 不会显示\n"
            cookie_list = "\n".join([f"{idx}. {cookie.cookie_name}" for idx, cookie in enumerate(cookies, 1)])
            state["_prompt"] = prompt_text + cookie_list
        else:
            # 单个模式：现有逻辑
            associated_cookies = await config.get_cookie(
                target=state["target"]["target"],
                site_name=state["site"].name,
                is_anonymous=False,
            )
            associated_cookie_ids = {cookie.id for cookie in associated_cookies}
            cookies = [cookie for cookie in cookies if cookie.id not in associated_cookie_ids]

            if not cookies:
                await add_cookie_target_matcher.finish(
                    '当前平台暂无可关联的 Cookie，请使用"添加cookie"命令添加或检查已关联的 Cookie'
                )

            state["_prompt"] = "请选择一个 Cookie，已关联的 Cookie 不会显示\n" + "\n".join(
                [f"{idx}. {cookie.cookie_name}" for idx, cookie in enumerate(cookies, 1)]
            )

        state["cookies"] = cookies

    @add_cookie_target_matcher.got("cookie_idx", MessageTemplate("{_prompt}"), [handle_cancel])
    async def got_cookie_idx(state: T_State, cookie_idx: str = ArgPlainText()):
        try:
            state["cookie"] = state["cookies"][int(cookie_idx) - 1]
        except Exception:
            await add_cookie_target_matcher.reject("序号错误")

    @add_cookie_target_matcher.handle()
    async def add_cookie_target_process(state: T_State):
        cookie = state["cookie"]

        if state.get("is_batch_mode", False):
            # 批量关联所有target
            success_count = 0
            failed_targets = []

            for target_info in state["batch_targets"]:
                try:
                    await config.add_cookie_target(target_info["target"], target_info["platform_name"], cookie.id)
                    success_count += 1
                except Exception:
                    # 这里可以根据需要获取target_name，但需要额外查询
                    failed_targets.append(target_info["target"])

            result_msg = f"已关联 Cookie: {cookie.cookie_name} 到 {success_count} 个订阅"
            if failed_targets:
                result_msg += f"\n失败的订阅: {', '.join(failed_targets)}"
            await add_cookie_target_matcher.finish(result_msg)
        else:
            # 单个关联：现有逻辑
            await config.add_cookie_target(state["target"]["target"], state["target"]["platform_name"], cookie.id)
            await add_cookie_target_matcher.finish(
                f"已关联 Cookie: {cookie.cookie_name} 到订阅 {state['site'].name} {state['target']['target']}"
            )
