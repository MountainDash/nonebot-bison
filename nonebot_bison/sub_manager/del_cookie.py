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

del_cookie_alc = Alconna(
    "删除cookie",
    meta=CommandMeta(description="Bison 删除 Cookie 指令", usage="输入“删除cookie”，跟随 Bot 提示信息进行"),
)

del_cookie_command = on_alconna(
    del_cookie_alc,
    use_cmd_start=True,
    auto_send_output=True,
    priority=5,
    block=True,
    aliases={"删除Cookie"},
    permission=admin_permission(),
    extensions=[
        BisonToMeCheckExtension(),
        BisonPrivateExtension(),
        BisonCancelExtension("删除中止"),
    ],
)


@del_cookie_command.handle()
async def del_cookie_handler(
    bot: Bot, event: Event, state: T_State, target_user_info: PlatformTarget = Depends(bison_target_user_info)
):
    # 1. 展示 Cookie 列表
    cookies = await config.get_cookie(is_anonymous=False)
    if not cookies:
        await UniMessage.text("暂无已添加的 Cookie\n请使用“添加cookie”命令添加").finish()
    res = "已添加的 Cookie 为：\n"
    state["cookie_table"] = {}
    for index, cookie in enumerate(cookies, 1):
        state["cookie_table"][index] = cookie
        res += f"{index} {cookie.site_name} {cookie.cookie_name} {len(cookie.targets)}个关联\n"
        if res[-1] != "\n":
            res += "\n"
    res += "请输入要删除的 Cookie 的序号\n输入'取消'中止"
    await MessageFactory(await parse_text(res)).send()

    # 2. 选择 Cookie 并删除
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
            cookie = state["cookie_table"][index]
            if cookie.targets:
                await UniMessage.text("只能删除未关联的 Cookie，请使用“取消关联cookie”命令取消关联").send()
                continue
            await config.delete_cookie_by_id(cookie.id)
        except KeyError:
            await UniMessage.text("序号错误").send()
            continue
        except Exception:
            await UniMessage.text("删除错误").send()
            continue
        else:
            await UniMessage.text("删除成功").finish()
    else:
        await UniMessage.text("输入失败").finish()
