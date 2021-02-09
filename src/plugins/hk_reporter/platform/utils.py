import time
import asyncio
import nonebot
from nonebot import logger
from collections import defaultdict
from .weibo import Weibo, get_user_info as weibo_user_info
from .bilibili import Bilibili, get_user_info as bilibili_user_info
from .rss import Rss, get_rss_info as rss_info
from .arkninghts import Arknights
from ..config import Config
from ..post import Post
from ..send import send_msgs

async def check_sub_target(target_type, target):
    if target_type == 'weibo':
        return await weibo_user_info(target)
    elif target_type == 'bilibili':
        return await bilibili_user_info(target)
    elif target_type == 'rss':
        return await rss_info(target)
    elif target_type == 'arknights':
        return '明日方舟游戏公告'
    else:
        return None


scheduler_last_run = defaultdict(lambda: 0)
async def scheduler(fun, target_type):
    platform_interval = {
            'weibo': 3
        }
    if (wait_time := time.time() - scheduler_last_run[target_type]) < platform_interval[target_type]:
        await asyncio.sleep(wait_time)
    await fun()

async def fetch_and_send(target_type: str):
    config = Config()
    platform_manager = {
            'bilibili': Bilibili(),
            'weibo': Weibo(),
            'rss': Rss(),
            'arknights': Arknights()
        }
    target = config.get_next_target(target_type)
    if not target:
        return
    logger.debug('try to fecth new posts from {}, target: {}'.format(target_type, target))
    new_posts: list[Post] = await platform_manager[target_type].fetch_new_post(target)
    send_list = config.target_user_cache[target_type][target]
    bot_list = list(nonebot.get_bots().values())
    bot = bot_list[0] if bot_list else None
    for new_post in new_posts:
        logger.warning('get new {} dynamic: {}'.format(target_type, new_post.url))
        logger.warning(new_post)
        if not bot:
            logger.warning('no bot connected')
        else:
            for to_send in send_list:
                send_msgs(bot, to_send['user'], to_send['user_type'], await new_post.generate_messages())
