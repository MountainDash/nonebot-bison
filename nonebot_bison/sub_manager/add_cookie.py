from json import JSONDecodeError
from typing import cast

from nonebot.adapters import Bot, Event
from nonebot.params import Depends
from nonebot.typing import T_State
from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_saa import PlatformTarget
from nonebot_plugin_waiter import waiter

from nonebot_bison.platform import platform_manager
from nonebot_bison.scheduler import scheduler_dict
from nonebot_bison.utils.site import CookieClientManager, is_cookie_client_manager

from .depends import (
    BisonCancelExtension,
    BisonPrivateExtension,
    BisonToMeCheckExtension,
    admin_permission,
    bison_target_user_info,
)
from .utils import common_platform

add_cookie_alc = Alconna(
    "添加cookie",
    meta=CommandMeta(description="Bison 添加 Cookie 指令", usage="输入“添加cookie”，跟随 Bot 提示信息进行"),
)

add_cookie_command = on_alconna(
    add_cookie_alc,
    use_cmd_start=True,
    auto_send_output=True,
    priority=5,
    block=True,
    permission=admin_permission(),
    extensions=[
        BisonToMeCheckExtension(),
        BisonPrivateExtension(),
        BisonCancelExtension("已中止添加cookie"),
    ],
)


@add_cookie_command.handle()
async def add_cookie_handler(
    bot: Bot, event: Event, state: T_State, target_user_info: PlatformTarget = Depends(bison_target_user_info)
):
    # 1. 选择平台
    await UniMessage.text(
        "请输入想要添加 Cookie 的平台，目前支持，请输入冒号左边的名称：\n"
        + "".join(
            [
                f"{platform_name}: {platform_manager[platform_name].name}\n"
                for platform_name in common_platform
                if is_cookie_client_manager(platform_manager[platform_name].site.client_mgr)
            ]
        )
        + "要查看全部平台请输入：“全部”\n中止添加cookie过程请输入：“取消”"
    ).send()

    @waiter(waits=["message"], keep_session=True)
    async def check_platform(event: Event):
        return event.get_plaintext().strip()

    async for platform in check_platform(timeout=600, retry=5, prompt=""):
        if platform is None:
            await UniMessage.text("等待超时！").finish()
        if platform == "全部":
            await UniMessage.text(
                "全部平台\n"
                + "\n".join(
                    [
                        f"{platform_name}: {platform.name}"
                        for platform_name, platform in platform_manager.items()
                        if is_cookie_client_manager(platform.site.client_mgr)
                    ]
                )
            ).send()
            continue
        elif platform == "取消":
            await UniMessage.text("已中止添加cookie").finish()
        elif platform in platform_manager and is_cookie_client_manager(platform_manager[platform].site.client_mgr):
            state["platform"] = platform
            break
        else:
            await UniMessage.text("平台输入错误，请重新输入").send()
            continue
    else:
        await UniMessage.text("输入失败").send()

    # 2. 输入 Cookie
    await UniMessage.text("请输入 Cookie").send()

    @waiter(waits=["message"], keep_session=True)
    async def check_cookie(event: Event):
        return event.get_plaintext().strip()

    async for cookie_text in check_cookie(timeout=600, retry=5, prompt=""):
        if cookie_text is None:
            await UniMessage.text("等待超时！").finish()
        client_mgr = cast(CookieClientManager, scheduler_dict[platform_manager[state["platform"]].site].client_mgr)
        if not await client_mgr.validate_cookie(cookie_text):
            await UniMessage.text(
                "无效的 Cookie，请检查后重新输入，详情见https://nonebot-bison.netlify.app/usage/cookie.html"
            ).send()
            continue
        try:
            cookie_name = await client_mgr.get_cookie_name(cookie_text)
            state["cookie"] = cookie_text
            state["cookie_name"] = cookie_name
            break
        except JSONDecodeError:
            await UniMessage.text(
                "获取 Cookie 名称失败，请检查后重新输入，详情见https://nonebot-bison.netlify.app/usage/cookie.html"
            ).send()
            continue
    else:
        await UniMessage.text("输入失败").finish()

    # 3. 添加 Cookie
    client_mgr = cast(CookieClientManager, scheduler_dict[platform_manager[state["platform"]].site].client_mgr)
    new_cookie = await client_mgr.add_identified_cookie(state["cookie"], state["cookie_name"])
    await UniMessage.text(
        f"已添加 Cookie: {new_cookie.cookie_name} 到平台 {state['platform']}" + "\n请使用“关联cookie”为 Cookie 关联订阅"
    ).finish()
