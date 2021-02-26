import nonebot
from nonebot import logger
from collections import defaultdict
from typing import Type
from .weibo import Weibo
from .bilibili import Bilibili
from .rss import Rss
from .platform import PlatformProto
from ..config import Config
from ..post import Post
from ..send import send_msgs

async def check_sub_target(target_type, target):
    return await platform_manager[target_type].get_account_name(target)

platform_manager: dict[str, PlatformProto] = {
        'bilibili': Bilibili(),
        'weibo': Weibo(),
        'rss': Rss()
    }

async def fetch_and_send(target_type: str):
    config = Config()
    target = config.get_next_target(target_type)
    if not target:
        return
    logger.debug('try to fecth new posts from {}, target: {}'.format(target_type, target))
    send_list = config.target_user_cache[target_type][target]
    bot_list = list(nonebot.get_bots().values())
    bot = bot_list[0] if bot_list else None
    to_send = await platform_manager[target_type].fetch_new_post(target, send_list)
    for user, send_list in to_send:
        for send_post in send_list:
            logger.debug('send to {}: {}'.format(user, send_post))
            if not bot:
                logger.warning('no bot connected')
            else:
                send_msgs(bot, user.user, user.user_type, await send_post.generate_messages())
