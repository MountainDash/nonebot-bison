from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import EventPlainText
from nonebot.typing import T_State
from nonebot_plugin_saa import MessageFactory

from nonebot_bison.config import config
from nonebot_bison.utils import parse_text

from .utils import gen_handle_cancel, only_allow_private


def do_del_cookie(del_cookie: type[Matcher]):
    handle_cancel = gen_handle_cancel(del_cookie, "删除中止")

    @del_cookie.handle()
    async def send_list(state: T_State, event: MessageEvent):
        await only_allow_private(event, del_cookie)
        cookies = await config.get_cookie(is_anonymous=False)
        if not cookies:
            await del_cookie.finish("暂无已添加的 Cookie\n请使用“添加cookie”命令添加")
        res = "已添加的 Cookie 为：\n"
        state["cookie_table"] = {}
        for index, cookie in enumerate(cookies, 1):
            state["cookie_table"][index] = cookie
            res += f"{index} {cookie.site_name} {cookie.cookie_name} {len(cookie.targets)}个关联\n"
            if res[-1] != "\n":
                res += "\n"
        res += "请输入要删除的 Cookie 的序号\n输入'取消'中止"
        await MessageFactory(await parse_text(res)).send()

    @del_cookie.receive(parameterless=[handle_cancel])
    async def do_del(
        state: T_State,
        index_str: str = EventPlainText(),
    ):
        try:
            index = int(index_str)
            cookie = state["cookie_table"][index]
            if cookie.targets:
                await del_cookie.reject("只能删除未关联的 Cookie，请使用“取消关联cookie”命令取消关联")
            await config.delete_cookie_by_id(cookie.id)
        except KeyError:
            await del_cookie.reject("序号错误")
        except Exception:
            await del_cookie.reject("删除错误")
        else:
            await del_cookie.finish("删除成功")
