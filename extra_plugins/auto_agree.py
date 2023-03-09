from typing import Union

from nonebot import on_request
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import FriendRequestEvent, GroupRequestEvent
from nonebot.log import logger

friend_req = on_request(priority=5)


@friend_req.handle()
async def add_superuser(bot: Bot, event: Union[GroupRequestEvent, FriendRequestEvent]):
    if str(event.user_id) not in bot.config.superusers:
        return

    if isinstance(event, FriendRequestEvent):
        await event.approve(bot)
        logger.info("add user {}".format(event.user_id))
    else:
        await event.approve(bot)
        logger.info("add group {}".format(event.group_id))
