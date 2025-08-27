from nonebot.adapters import Bot, Event
from nonebot.params import Depends
from nonebot.typing import T_State
from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_saa import MessageFactory, PlatformTarget
from nonebot_plugin_waiter import waiter

from nonebot_bison.config import config
from nonebot_bison.utils import parse_text

from .depends import (
    BisonCancelExtension,
    BisonPrivateExtension,
    BisonToMeCheckExtension,
    admin_permission,
    bison_target_user_info,
)

del_cookie_target_alc = Alconna(
    "取消关联cookie",
    meta=CommandMeta(description="Bison 取消 Cookie 关联指令", usage="输入“取消关联cookie”，跟随 Bot 提示信息进行"),
)

del_cookie_target_command = on_alconna(
    del_cookie_target_alc,
    use_cmd_start=True,
    auto_send_output=True,
    priority=5,
    block=True,
    aliases={"取消关联Cookie"},
    permission=admin_permission(),
    extensions=[
        BisonToMeCheckExtension(),
        BisonPrivateExtension(),
        BisonCancelExtension("取消关联中止"),
    ],
)


@del_cookie_target_command.handle()
async def del_cookie_target_handler(
    bot: Bot, event: Event, state: T_State, target_user_info: PlatformTarget = Depends(bison_target_user_info)
):
    # 1. 展示已关联 Cookie 列表
    cookie_targets = await config.get_cookie_target()
    if not cookie_targets:
        await UniMessage.text("暂无已关联 Cookie\n请使用“添加cookie”命令添加关联").finish()
    res = "已关联的 Cookie 为：\n"
    state["cookie_target_table"] = {}
    for index, cookie_target in enumerate(cookie_targets, 1):
        friendly_name = cookie_target.cookie.cookie_name
        state["cookie_target_table"][index] = {
            "platform_name": cookie_target.target.platform_name,
            "target": cookie_target.target,
            "friendly_name": friendly_name,
            "cookie_target": cookie_target,
        }
        res += f"{index} {cookie_target.target.platform_name} {cookie_target.target.target_name} {friendly_name}\n"
        if res[-1] != "\n":
            res += "\n"
    res += "请输入要删除的关联的序号\n输入'取消'中止"
    await MessageFactory(await parse_text(res)).send()

    # 2. 选择并删除关联
    @waiter(waits=["message"], keep_session=True)
    async def check_index(event: Event):
        return event.get_plaintext().strip()

    async for index_str in check_index(timeout=600, retry=5, prompt=""):
        if index_str is None:
            await UniMessage.text("等待超时！").finish()
        if index_str == "取消":
            await UniMessage.text("取消关联中止").finish()
        try:
            index = int(index_str)
            await config.delete_cookie_target_by_id(state["cookie_target_table"][index]["cookie_target"].id)
        except Exception:
            await UniMessage.text("删除错误").send()
            continue
        else:
            await UniMessage.text("删除成功").finish()
    else:
        await UniMessage.text("输入失败").finish()
