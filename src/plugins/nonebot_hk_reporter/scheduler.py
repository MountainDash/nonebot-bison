from nonebot import get_driver, logger
from .send import do_send_msgs
from .platform import fetch_and_send, platform_manager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def _start():
    scheduler.configure({"apscheduler.timezone": "Asia/Shanghai"})
    scheduler.start()

get_driver().on_startup(_start)

for platform_name, platform in platform_manager.items():
    if isinstance(platform.schedule_interval, int):
        logger.info(f'start scheduler for {platform_name} with interval {platform.schedule_interval}')
        scheduler.add_job(
                fetch_and_send, 'interval', seconds=platform.schedule_interval,
                args=(platform_name,))

@scheduler.scheduled_job('interval', seconds=1)
async def _send_msgs():
    await do_send_msgs()
