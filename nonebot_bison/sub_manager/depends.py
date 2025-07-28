from nonebot_plugin_alconna import Extension
from nonebot.adapters import Bot, Event, Message
from nonebot.matcher import Matcher
from nonebot_plugin_alconna import Alconna, UniMessage
from nonebot_plugin_saa import extract_target, PlatformTarget
from nonebot.typing import T_State
from nonebot_bison.plugin_config import plugin_config
import contextlib
from nonebot.permission import SUPERUSER

def admin_permission():
    permission = SUPERUSER
    with contextlib.suppress(ImportError):
        from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

        permission = permission | GROUP_ADMIN | GROUP_OWNER

    return permission

async def bison_target_user_info(event: Event) -> PlatformTarget:
    return extract_target(event)


# 拜松的干员id为`char_325_bison`
class BisonToMeCheckExtension(Extension):
    @property
    def priority(self) -> int:
        return 3251

    @property
    def id(self) -> str:
        return "BisonToMeCheckExtension"

    async def permission_check(self, bot: Bot, event: Event, command: Alconna):
        from nonebot import logger
        if plugin_config.bison_to_me:
            return event.is_tome()
        else:
            return True


class BisonPrivateExtension(Extension):
    @property
    def priority(self) -> int:
        return 3252

    @property
    def id(self) -> str:
        return "BisonPrivateExtension"

    async def permission_check(self, bot: Bot, event: Event, command: Alconna):
        if not (hasattr(event, "message_type") and getattr(event, "message_type") == "private"):
            await bot.send(event, "请在私聊中使用此命令")
            return False
        return True


class BisonCancelExtension(Extension):
    def __init__(self, message: str = "已中止操作"):
        self.message = message

    @property
    def priority(self) -> int:
        return 3253

    @property
    def id(self) -> str:
        return "BisonStopExtension"

    async def permission_check(self, bot: Bot, event: Event, command: Alconna):
        if event.get_plaintext().strip() == "取消":
            await bot.send(event, self.message)
            return False
        return True
