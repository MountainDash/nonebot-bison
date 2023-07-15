from nonebot import on_request
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import GroupRequestEvent, FriendRequestEvent

friend_req = on_request(priority=5)


@friend_req.handle()
async def add_superuser(bot: Bot, event: GroupRequestEvent | FriendRequestEvent):
    if str(event.user_id) not in bot.config.superusers:
        return

    if isinstance(event, FriendRequestEvent):
        await event.approve(bot)
        logger.info(f"add user {event.user_id}")
    else:
        await event.approve(bot)
        logger.info(f"add group {event.group_id}")
