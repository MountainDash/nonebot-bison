import asyncio
from datetime import datetime

from nonebot import on_command
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.rule import Rule, to_me
from nonebot.permission import SUPERUSER
from nonebot_plugin_saa import TargetQQGroup
from nonebot.params import ArgStr, ArgPlainText
from nonebot.adapters import Bot, MessageTemplate
from nonebot.adapters.onebot.v11.event import PrivateMessageEvent

from .add_sub import do_add_sub
from .del_sub import do_del_sub
from .query_sub import do_query_sub
from .utils import common_platform, admin_permission, gen_handle_cancel, configurable_to_me, set_target_user_info

add_sub_matcher = on_command(
    "添加订阅",
    rule=configurable_to_me,
    permission=admin_permission(),
    priority=5,
    block=True,
)
add_sub_matcher.handle()(set_target_user_info)
do_add_sub(add_sub_matcher)


query_sub_matcher = on_command("查询订阅", rule=configurable_to_me, priority=5, block=True)
query_sub_matcher.handle()(set_target_user_info)
do_query_sub(query_sub_matcher)


del_sub_matcher = on_command(
    "删除订阅",
    rule=configurable_to_me,
    permission=admin_permission(),
    priority=5,
    block=True,
)
del_sub_matcher.handle()(set_target_user_info)
do_del_sub(del_sub_matcher)

group_manage_matcher = on_command("群管理", rule=to_me(), permission=SUPERUSER, priority=4, block=True)

group_handle_cancel = gen_handle_cancel(group_manage_matcher, "已取消")


@group_manage_matcher.handle()
async def send_group_list(bot: Bot, event: PrivateMessageEvent, state: T_State):
    groups = await bot.call_api("get_group_list")
    res_text = "请选择需要管理的群：\n"
    group_number_idx = {}
    for idx, group in enumerate(groups, 1):
        group_number_idx[idx] = group["group_id"]
        res_text += f'{idx}. {group["group_id"]} - {group["group_name"]}\n'
    res_text += "请输入左侧序号\n中止操作请输入'取消'"
    # await group_manage_matcher.send(res_text)
    state["_prompt"] = res_text
    state["group_number_idx"] = group_number_idx


@group_manage_matcher.got("group_idx", MessageTemplate("{_prompt}"), [group_handle_cancel])
async def do_choose_group_number(state: T_State, event: PrivateMessageEvent, group_idx: str = ArgPlainText()):
    group_number_idx: dict[int, int] = state["group_number_idx"]
    assert group_number_idx
    idx = int(group_idx)
    if idx not in group_number_idx.keys():
        await group_manage_matcher.reject("请输入正确序号")
    state["group_idx"] = idx
    group_number_idx: dict[int, int] = state["group_number_idx"]
    idx: int = state["group_idx"]
    group_id = group_number_idx[idx]
    state["target_user_info"] = TargetQQGroup(group_id=group_id)


@group_manage_matcher.got("command", "请输入需要使用的命令：添加订阅，查询订阅，删除订阅，取消", [group_handle_cancel])
async def do_dispatch_command(
    bot: Bot,
    event: PrivateMessageEvent,
    state: T_State,
    matcher: Matcher,
    command: str = ArgStr(),
):
    if command not in {"添加订阅", "查询订阅", "删除订阅", "取消"}:
        await group_manage_matcher.reject("请输入正确的命令")
    permission = await matcher.update_permission(bot, event)
    new_matcher = Matcher.new(
        "message",
        Rule(),
        permission,
        handlers=None,
        temp=True,
        priority=0,
        block=True,
        plugin=matcher.plugin,
        module=matcher.module,
        expire_time=datetime.now(),
        default_state=matcher.state,
        default_type_updater=matcher.__class__._default_type_updater,
        default_permission_updater=matcher.__class__._default_permission_updater,
    )
    if command == "查询订阅":
        do_query_sub(new_matcher)
    elif command == "添加订阅":
        do_add_sub(new_matcher)
    else:
        do_del_sub(new_matcher)
    new_matcher_ins = new_matcher()
    asyncio.create_task(new_matcher_ins.run(bot, event, state))


__all__ = [
    "common_platform",
    "add_sub_matcher",
    "query_sub_matcher",
    "del_sub_matcher",
    "group_manage_matcher",
]
