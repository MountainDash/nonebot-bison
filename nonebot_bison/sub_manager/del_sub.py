from typing import cast

from nonebot.adapters import Bot, Event
from nonebot.params import Depends
from nonebot.typing import T_State
from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_saa import MessageFactory, PlatformTarget
from nonebot_plugin_waiter import waiter

from nonebot_bison.config import config
from nonebot_bison.platform import platform_manager
from nonebot_bison.types import Category
from nonebot_bison.utils import parse_text

from .depends import BisonCancelExtension, BisonToMeCheckExtension, admin_permission, bison_target_user_info

del_sub_alc = Alconna(
    "删除订阅",
    meta=CommandMeta(description="Bison 删除订阅指令", usage="输入“删除订阅”，跟随 Bot 提示信息进行"),
)

del_sub_command = on_alconna(
    del_sub_alc,
    use_cmd_start=True,
    auto_send_output=True,
    priority=5,
    block=True,
    permission=admin_permission(),
    extensions=[
        BisonToMeCheckExtension(),
        BisonCancelExtension("删除中止"),
    ],
)


@del_sub_command.handle()
async def del_sub_handler(
    bot: Bot, event: Event, state: T_State, target_user_info: PlatformTarget = Depends(bison_target_user_info)
):
    # 1. 获取用户订阅列表
    user_info = cast(PlatformTarget, state.get("target_user_info"))
    sub_list = await config.list_subscribe(user_info)
    if not sub_list:
        await UniMessage.text("暂无已订阅账号\n请使用“添加订阅”命令添加订阅").finish()
    res = "订阅的帐号为：\n"
    state["sub_table"] = {}
    for index, sub in enumerate(sub_list, 1):
        state["sub_table"][index] = {
            "platform_name": sub.target.platform_name,
            "target": sub.target.target,
        }
        res += f"{index} {sub.target.platform_name} {sub.target.target_name} {sub.target.target}\n"
        if platform := platform_manager.get(sub.target.platform_name):
            if platform.categories:
                res += " [{}]".format(", ".join(platform.categories[Category(x)] for x in sub.categories))
            if platform.enable_tag:
                res += " {}".format(", ".join(sub.tags))
        else:
            res += f" （平台 {sub.target.platform_name} 已失效，请删除此订阅）"
        if res[-1] != "\n":
            res += "\n"
    res += "请输入要删除的订阅的序号\n输入'取消'中止"
    await MessageFactory(await parse_text(res)).send()

    # 2. 选择订阅并删除
    @waiter(waits=["message"], keep_session=True)
    async def check_index(event: Event):
        return event.get_plaintext().strip()

    async for index_str in check_index(timeout=600, retry=5, prompt=""):
        if index_str is None:
            await UniMessage.text("等待超时！").finish()
        if index_str == "取消":
            await UniMessage.text("删除中止").finish()
        try:
            index = int(index_str)
            await config.del_subscribe(user_info, **state["sub_table"][index])
        except Exception:
            await UniMessage.text("删除错误").send()
            continue
        else:
            await UniMessage.text("删除成功").finish()
    else:
        await UniMessage.text("输入失败").finish()
