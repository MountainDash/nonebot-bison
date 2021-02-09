from nonebot import on_request, logger
from nonebot.adapters.cqhttp import Bot, Event
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.permission import PRIVATE_FRIEND
from nonebot.adapters.cqhttp.event import FriendRequestEvent, GroupRequestEvent

friend_req = on_request(priority=5)

@friend_req.handle()
async def add_superuser(bot: Bot, event: FriendRequestEvent, state: T_State):
    if event.user_id in bot.config.superusers:
        await event.approve(bot)
        logger.info('add user {}'.format(event.user_id))

@friend_req.handle()
async def agree_to_group(bot: Bot, event: GroupRequestEvent, state: T_State):
    if event.sub_type == 'invite' and event.user_id in bot.config.superusers:
        await event.approve(bot)
        logger.info('add group {}'.format(event.group_id))
