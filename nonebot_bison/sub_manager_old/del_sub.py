from nonebot.matcher import Matcher
from nonebot.params import Arg, EventPlainText
from nonebot.typing import T_State
from nonebot_plugin_saa import MessageFactory, PlatformTarget

from nonebot_bison.config import config
from nonebot_bison.platform import platform_manager
from nonebot_bison.types import Category
from nonebot_bison.utils import parse_text

from .utils import ensure_user_info, gen_handle_cancel


def do_del_sub(del_sub: type[Matcher]):
    handle_cancel = gen_handle_cancel(del_sub, "删除中止")

    del_sub.handle()(ensure_user_info(del_sub))

    @del_sub.handle()
    async def send_list(state: T_State, user_info: PlatformTarget = Arg("target_user_info")):
        sub_list = await config.list_subscribe(user_info)
        if not sub_list:
            await del_sub.finish("暂无已订阅账号\n请使用“添加订阅”命令添加订阅")
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

    @del_sub.receive(parameterless=[handle_cancel])
    async def do_del(
        state: T_State,
        index_str: str = EventPlainText(),
        user_info: PlatformTarget = Arg("target_user_info"),
    ):
        try:
            index = int(index_str)
            await config.del_subscribe(user_info, **state["sub_table"][index])
        except Exception:
            await del_sub.reject("删除错误")
        else:
            await del_sub.finish("删除成功")
