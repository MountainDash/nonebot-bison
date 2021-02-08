from nonebot import require
from .send import do_send_msgs
from .platform.utils import fetch_and_send
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler: AsyncIOScheduler = require('nonebot_plugin_apscheduler').scheduler

@scheduler.scheduled_job('interval', seconds=10)
async def weibo_check():
    await fetch_and_send('weibo')

@scheduler.scheduled_job('interval', seconds=10)
async def bilibili_check():
    await fetch_and_send('bilibili')


@scheduler.scheduled_job('interval', seconds=30)
async def rss_check():
    await fetch_and_send('rss')

@scheduler.scheduled_job('interval', seconds=1)
async def _():
    await do_send_msgs()
