from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText
from nonebot.typing import T_State
from nonebot_plugin_saa import MessageFactory

from nonebot_bison.config import config
from nonebot_bison.utils import parse_text

from .utils import (
    gen_handle_cancel,
    generate_cookie_target_list_by_platform,
    generate_cookie_target_platform_list_text,
    only_allow_private,
)


def do_del_cookie_target(del_cookie_target: type[Matcher]):
    handle_cancel = gen_handle_cancel(del_cookie_target, "取消关联中止")

    @del_cookie_target.handle()
    async def send_list(state: T_State, event: MessageEvent):
        await only_allow_private(event, del_cookie_target)
        res = await generate_cookie_target_platform_list_text(del_cookie_target, state)
        await MessageFactory(await parse_text(res)).send()

    @del_cookie_target.got("platform_name", parameterless=[handle_cancel])
    async def got_platform_name(state: T_State, platform_name: str = ArgPlainText()):
        platform_name = platform_name.strip()
        if platform_name not in state["platform_table"]:
            await del_cookie_target.reject("平台名称错误，请输入有关联的平台名称")
        state["selected_platform"] = platform_name

    @del_cookie_target.handle()
    async def show_platform_cookie_targets(state: T_State):
        selected_platform = state["selected_platform"]
        res = await generate_cookie_target_list_by_platform(del_cookie_target, state, selected_platform)
        await MessageFactory(await parse_text(res)).send()

    @del_cookie_target.got("target_idx", parameterless=[handle_cancel])
    async def got_target_idx(state: T_State, target_idx: str = ArgPlainText()):
        try:
            # 解析多个序号（用空格分隔）
            index_strs = target_idx.strip().split()
            if not index_strs:
                await del_cookie_target.reject("请输入序号")

            selected_cookie_targets = []
            invalid_indices = []

            for idx_str in index_strs:
                try:
                    index = int(idx_str)
                    if index not in state["cookie_target_table"]:
                        invalid_indices.append(idx_str)
                    else:
                        selected_cookie_targets.append(state["cookie_target_table"][index]["cookie_target"])
                except ValueError:
                    invalid_indices.append(idx_str)

            if invalid_indices:
                await del_cookie_target.reject(f"序号错误：{', '.join(invalid_indices)}，请输入正确的数字序号")

            if not selected_cookie_targets:
                await del_cookie_target.reject("没有选择有效的序号")

            state["selected_cookie_targets"] = selected_cookie_targets
        except Exception:
            await del_cookie_target.reject("输入格式错误，请输入数字序号（多个用空格分隔）")

    @del_cookie_target.handle()
    async def do_del(state: T_State):
        selected_cookie_targets = state["selected_cookie_targets"]
        success_count = 0
        failed_targets = []

        for cookie_target in selected_cookie_targets:
            try:
                await config.delete_cookie_target_by_id(cookie_target.id)
                success_count += 1
            except Exception:
                target_info = f"{cookie_target.target.target_name}({cookie_target.cookie.cookie_name})"
                failed_targets.append(target_info)

        # 生成结果消息
        if success_count == len(selected_cookie_targets):
            if success_count == 1:
                await del_cookie_target.finish("取消关联成功")
            else:
                await del_cookie_target.finish(f"批量取消关联成功，共处理 {success_count} 个关联")
        elif success_count > 0:
            result_msg = f"部分取消关联成功：成功 {success_count} 个"
            if failed_targets:
                result_msg += f"，失败 {len(failed_targets)} 个：\n" + "\n".join(failed_targets)
            await del_cookie_target.finish(result_msg)
        else:
            fail_msg = "取消关联失败"
            if failed_targets:
                fail_msg += "，失败的关联：\n" + "\n".join(failed_targets)
            await del_cookie_target.finish(fail_msg)
