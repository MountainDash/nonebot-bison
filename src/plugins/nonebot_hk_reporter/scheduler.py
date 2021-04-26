from nonebot import require, get_driver
from .send import do_send_msgs
from .platform.utils import fetch_and_send
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def _start():
    scheduler.configure({"apscheduler.timezone": "Asia/Shanghai"})
    scheduler.start()

get_driver().on_startup(_start)

@scheduler.scheduled_job('interval', seconds=10)
async def weibo_check():
    await fetch_and_send('weibo')

@scheduler.scheduled_job('interval', seconds=10)
async def bilibili_check():
    await fetch_and_send('bilibili')


@scheduler.scheduled_job('interval', seconds=30)
async def rss_check():
    await fetch_and_send('rss')


# @scheduler.scheduled_job('interval', seconds=30)
# async def wechat_check():
#     await fetch_and_send('wechat')

@scheduler.scheduled_job('interval', seconds=1)
async def _send_msgs():
    await do_send_msgs()
