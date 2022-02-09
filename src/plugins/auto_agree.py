from nonebot.typing import T_State
from nonebot import logger, on_request
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.adapters.onebot.v11.permission import PRIVATE_FRIEND
from nonebot.adapters.onebot.v11.event import (
    RequestEvent,
    GroupRequestEvent,
    FriendRequestEvent,
)

friend_req = on_request(priority=5)


@friend_req.handle()
async def add_superuser(bot: Bot, event: RequestEvent, state: T_State):
    if str(event.user_id) in bot.config.superusers and event.request_type == "private":
        await event.approve(bot)
        logger.info("add user {}".format(event.user_id))
    elif (
        event.sub_type == "invite"
        and str(event.user_id) in bot.config.superusers
        and event.request_type == "group"
    ):
        await event.approve(bot)
        logger.info("add group {}".format(event.group_id))
