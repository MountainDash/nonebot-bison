from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import EventPlainText
from nonebot.typing import T_State
from nonebot_plugin_saa import MessageFactory

from nonebot_bison.config import config
from nonebot_bison.utils import parse_text

from .utils import gen_handle_cancel, only_allow_private


def do_del_cookie_target(del_cookie_target: type[Matcher]):
    handle_cancel = gen_handle_cancel(del_cookie_target, "取消关联中止")

    @del_cookie_target.handle()
    async def send_list(state: T_State, event: MessageEvent):
        await only_allow_private(event, del_cookie_target)
        cookie_targets = await config.get_cookie_target()
        if not cookie_targets:
            await del_cookie_target.finish("暂无已关联 Cookie\n请使用“添加cookie”命令添加关联")
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

    @del_cookie_target.receive(parameterless=[handle_cancel])
    async def do_del(
        state: T_State,
        index_str: str = EventPlainText(),
    ):
        try:
            index = int(index_str)
            await config.delete_cookie_target_by_id(state["cookie_target_table"][index]["cookie_target"].id)
        except Exception:
            await del_cookie_target.reject("删除错误")
        else:
            await del_cookie_target.finish("删除成功")
