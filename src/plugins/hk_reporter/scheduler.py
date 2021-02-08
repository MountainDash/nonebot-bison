import nonebot
from .config import Config
from nonebot import require
from nonebot import logger
from .platform.bilibili import Bilibili
from .platform.weibo import Weibo
from .platform.rss import Rss
from .post import Post
from .send import send_msgs, do_send_msgs
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler: AsyncIOScheduler = require('nonebot_plugin_apscheduler').scheduler
config: Config = Config()
weibo: Weibo = Weibo()
bilibili: Bilibili = Bilibili()
rss: Rss = Rss()

@scheduler.scheduled_job('interval', seconds=10)
async def weibo_check():
    target = config.get_next_target('weibo')
    if not target:
        return
    logger.debug('try to fecth new posts from weibo, target: {}'.format(target))
    new_weibos: list[Post] = await weibo.fetch_new_post(target)
    send_list = config.target_user_cache['weibo'][target]
    bot_list = list(nonebot.get_bots().values())
    bot = bot_list[0] if bot_list else None
    for new_weibo in new_weibos:
        logger.warning('get new weibo post: {}'.format(new_weibo.url))
        if not bot:
            logger.warning('no bot connected')
        else:
            for to_send in send_list:
                send_msgs(bot, to_send['user'], to_send['user_type'], await new_weibo.generate_messages())

@scheduler.scheduled_job('interval', seconds=10)
async def bilibili_check():
    target = config.get_next_target('bilibili')
    if not target:
        return
    logger.debug('try to fecth new posts from bilibili, target: {}'.format(target))
    new_posts: list[Post] = await bilibili.fetch_new_post(target)
    send_list = config.target_user_cache['bilibili'][target]
    bot_list = list(nonebot.get_bots().values())
    bot = bot_list[0] if bot_list else None
    for new_post in new_posts:
        logger.warning('get new bilibili dynamic: {}'.format(new_post.url))
        logger.warning(new_post)
        if not bot:
            logger.warning('no bot connected')
        else:
            for to_send in send_list:
                send_msgs(bot, to_send['user'], to_send['user_type'], await new_post.generate_messages())

@scheduler.scheduled_job('interval', seconds=30)
async def rss_check():
    target = config.get_next_target('rss')
    if not target:
        return
    logger.debug('try to fecth new posts from rss, target: {}'.format(target))
    new_posts: list[Post] = await rss.fetch_new_post(target)
    send_list = config.target_user_cache['rss'][target]
    bot_list = list(nonebot.get_bots().values())
    bot = bot_list[0] if bot_list else None
    for new_post in new_posts:
        logger.warning('get new rss entry: {}'.format(new_post.url))
        logger.warning(new_post)
        if not bot:
            logger.warning('no bot connected')
        else:
            for to_send in send_list:
                send_msgs(bot, to_send['user'], to_send['user_type'], await new_post.generate_messages())

@scheduler.scheduled_job('interval', seconds=1)
async def _():
    await do_send_msgs()
