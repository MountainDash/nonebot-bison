from nonebot_plugin_alconna import on_alconna, Alconna, CommandMeta
from nonebot_plugin_waiter import waiter, prompt
from nonebot.adapters import Bot, Event
from nonebot.typing import T_State
from nonebot.params import Depends
from typing import cast
from nonebot_bison.config import config
from nonebot_bison.platform import platform_manager
from nonebot_bison.utils import parse_text
from nonebot_plugin_saa import MessageFactory, PlatformTarget

from nonebot_bison.config.db_model import Cookie
from .utils import generate_sub_list_text
from .depends import BisonToMeCheckExtension, BisonPrivateExtension, BisonCancelExtension, admin_permission, bison_target_user_info

add_cookie_target_alc = Alconna(
    "关联cookie",
    meta=CommandMeta(
        description="Bison 关联 Cookie 指令",
        usage="输入“关联cookie”，跟随 Bot 提示信息进行"
    ),
)

add_cookie_target_command = on_alconna(
    add_cookie_target_alc,
    use_cmd_start=True,
    auto_send_output=True,
    priority=5,
    block=True,
    permission=admin_permission(),
    aliases={"关联Cookie"},
    extensions=[
        BisonToMeCheckExtension(),
        BisonPrivateExtension(),
        BisonCancelExtension("已中止关联cookie"),
    ]
)


@add_cookie_target_command.handle()
async def add_cookie_target_handler(
        bot: Bot,
        event: Event,
        state: T_State,
        target_user_info: PlatformTarget = Depends(bison_target_user_info)):
    # 1. 展示订阅列表，选择订阅
    res = await generate_sub_list_text(
        add_cookie_target_command, state, is_index=True, is_show_cookie=True, is_hide_no_cookie_platfrom=True
    )
    res += "请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
    await MessageFactory(await parse_text(res)).send()

    @waiter(waits=["message"], keep_session=True)
    async def check_target_idx(event: Event):
        return event.get_plaintext().strip()

    async for target_idx in check_target_idx(timeout=600, retry=5, prompt=""):
        if target_idx is None:
            await add_cookie_target_command.finish("等待超时！")
        if target_idx == "取消":
            await add_cookie_target_command.finish("已中止关联cookie")
        try:
            state["target"] = cast(dict, state["sub_table"][int(target_idx)])
            state["site"] = platform_manager[state["target"]["platform_name"]].site
            break
        except Exception:
            await add_cookie_target_command.send("序号错误")
            continue
    else:
        await add_cookie_target_command.finish("输入失败")

    # 2. 获取 site 的所有实名 cookie，再排除掉已经关联的 cookie，剩下的就是可以关联的 cookie
    cookies = await config.get_cookie(site_name=state["site"].name, is_anonymous=False)
    associated_cookies = await config.get_cookie(
        target=state["target"]["target"],
        site_name=state["site"].name,
        is_anonymous=False,
    )
    associated_cookie_ids = {cookie.id for cookie in associated_cookies}
    cookies = [
        cookie for cookie in cookies if cookie.id not in associated_cookie_ids]
    if not cookies:
        await add_cookie_target_command.finish(
            "当前平台暂无可关联的 Cookie，请使用“添加cookie”命令添加或检查已关联的 Cookie"
        )
    state["cookies"] = cookies

    cookie_list_text = "请选择一个 Cookie，已关联的 Cookie 不会显示\n" + "\n".join(
        [f"{idx}. {cookie.cookie_name}" for idx,
            cookie in enumerate(cookies, 1)]
    )
    await add_cookie_target_command.send(cookie_list_text)

    @waiter(waits=["message"], keep_session=True)
    async def check_cookie_idx(event: Event):
        return event.get_plaintext().strip()

    async for cookie_idx in check_cookie_idx(timeout=600, retry=5, prompt=""):
        if cookie_idx is None:
            await add_cookie_target_command.finish("等待超时！")
        if cookie_idx == "取消":
            await add_cookie_target_command.finish("已中止关联cookie")
        try:
            idx = int(cookie_idx)
            state["cookie"] = cast(object, state["cookies"][idx - 1])
            break
        except Exception:
            await add_cookie_target_command.send("序号错误，请重新输入")
            continue
    else:
        await add_cookie_target_command.finish("输入失败")

    # 3. 关联 Cookie
    cookie = cast("Cookie", state["cookie"])
    await config.add_cookie_target(
        state["target"]["target"],
        state["target"]["platform_name"],
        cookie.id
    )
    await add_cookie_target_command.finish(
        f"已关联 Cookie: {cookie.cookie_name} 到订阅 {state['site'].name} {state['target']['target']}"
    )
