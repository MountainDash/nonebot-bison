import asyncio
from datetime import datetime

from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11.event import PrivateMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot.permission import SUPERUSER
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_saa import PlatformTarget, TargetQQGroup
from nonebot_plugin_waiter import waiter

from .add_sub import add_sub_handler
from .del_sub import del_sub_handler
from .depends import BisonCancelExtension, BisonToMeCheckExtension, bison_target_user_info
from .query_sub import query_sub_handler

_COMMAND_DISPATCH_TASKS: set[asyncio.Task] = set()

group_manage_alc = Alconna(
    "群管理",
    meta=CommandMeta(description="Bison 群管理入口", usage="输入“群管理”，跟随 Bot 提示信息进行"),
)

group_manage_command = on_alconna(
    group_manage_alc,
    use_cmd_start=True,
    auto_send_output=True,
    priority=4,
    block=True,
    permission=SUPERUSER,
    extensions=[
        BisonToMeCheckExtension(),
        BisonCancelExtension("已取消"),
    ],
)


@group_manage_command.handle()
async def group_manage_handler(
    bot: Bot,
    event: PrivateMessageEvent,
    state: T_State,
    matcher: Matcher,
    target_user_info: PlatformTarget = Depends(bison_target_user_info),
):
    # 1. 获取群列表
    groups = await bot.call_api("get_group_list")
    res_text = "请选择需要管理的群：\n"
    group_number_idx = {}
    for idx, group in enumerate(groups, 1):
        group_number_idx[idx] = group["group_id"]
        res_text += f"{idx}. {group['group_id']} - {group['group_name']}\n"
    res_text += "请输入左侧序号\n中止操作请输入'取消'"
    await UniMessage.text(res_text).send()

    @waiter(waits=["message"], keep_session=True)
    async def check_group_idx(_event: PrivateMessageEvent):
        return _event.get_plaintext().strip()

    async for group_idx in check_group_idx(timeout=600, retry=5, prompt=""):
        if group_idx is None:
            await UniMessage.text("等待超时！").finish()
        if group_idx == "取消":
            await UniMessage.text("已取消").finish()
        try:
            idx = int(group_idx)
            group_id = group_number_idx[idx]
            state["target_user_info"] = TargetQQGroup(group_id=group_id)
            break
        except Exception:
            await UniMessage.text("请输入正确序号").send()
            continue
    else:
        await UniMessage.text("输入失败").finish()

    # 2. 分发子命令
    sub_cmd_text = "请输入需要使用的命令：添加订阅，查询订阅，删除订阅，取消"
    sub_cmd_map = {
        "添加订阅": add_sub_handler,
        "查询订阅": query_sub_handler,
        "删除订阅": del_sub_handler,
    }
    await UniMessage.text(sub_cmd_text).send()

    @waiter(waits=["message"], keep_session=True)
    async def check_sub_cmd(event: Event):
        return event.get_plaintext().strip()

    async for command in check_sub_cmd(timeout=600, retry=5, prompt=""):
        if command is None:
            await UniMessage.text("等待超时！").finish()
        if command not in {"添加订阅", "查询订阅", "删除订阅", "取消"}:
            await UniMessage.text("请输入正确的命令").send()
            continue
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
        if command == "取消":
            await UniMessage.text("已取消").finish()
        elif sub_handler := sub_cmd_map.get(command, None):
            break

    else:
        await UniMessage.text("输入失败").finish()

    new_matcher.append_handler(sub_handler)
    new_matcher_ins = new_matcher()

    task = asyncio.create_task(new_matcher_ins.run(bot, event, state))
    _COMMAND_DISPATCH_TASKS.add(task)
    task.add_done_callback(_COMMAND_DISPATCH_TASKS.discard)
