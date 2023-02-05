from apscheduler.schedulers.asyncio import AsyncIOScheduler

aps = AsyncIOScheduler(timezone="Asia/Shanghai")


def start_scheduler():
    aps.configure({"apscheduler.timezone": "Asia/Shanghai"})
    aps.start()
