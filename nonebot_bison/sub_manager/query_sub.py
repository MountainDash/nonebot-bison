from typing import cast

from nonebot.adapters import Bot, Event
from nonebot.params import Depends
from nonebot.typing import T_State
from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna
from nonebot_plugin_saa import MessageFactory, PlatformTarget

from nonebot_bison.config import config
from nonebot_bison.platform import platform_manager
from nonebot_bison.types import Category
from nonebot_bison.utils import parse_text

from .depends import BisonCancelExtension, BisonToMeCheckExtension, admin_permission, bison_target_user_info

query_sub_alc = Alconna(
    "查询订阅",
    meta=CommandMeta(description="Bison 查询订阅指令", usage="输入“查询订阅”，跟随 Bot 提示信息进行"),
)

query_sub_command = on_alconna(
    query_sub_alc,
    use_cmd_start=True,
    auto_send_output=True,
    priority=5,
    block=True,
    permission=admin_permission(),
    extensions=[
        BisonToMeCheckExtension(),
        BisonCancelExtension("查询中止"),
    ],
)


@query_sub_command.handle()
async def query_sub_handler(
    bot: Bot, event: Event, state: T_State, target_user_info: PlatformTarget = Depends(bison_target_user_info)
):
    user_info = cast(PlatformTarget, state.get("target_user_info"))
    sub_list = await config.list_subscribe(user_info)
    if not sub_list:
        await query_sub_command.finish("暂无已订阅账号\n请使用“添加订阅”命令添加订阅")
    res = "订阅的帐号为：\n"
    for sub in sub_list:
        res += f"{sub.target.platform_name} {sub.target.target_name} {sub.target.target}\n"
        if platform := platform_manager.get(sub.target.platform_name):
            if platform.categories:
                res += " [{}]".format(", ".join(platform.categories[Category(x)] for x in sub.categories))
            if platform.enable_tag:
                res += " {}".format(", ".join(sub.tags))
        else:
            res += f" （平台 {sub.target.platform_name} 已失效，请删除此订阅）"
        if res[-1] != "\n":
            res += "\n"
    await MessageFactory(await parse_text(res)).send()
    await query_sub_command.finish()
