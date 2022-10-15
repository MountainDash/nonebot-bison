import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from nonebot.log import LoguruHandler

from ..plugin_config import plugin_config
from ..send import do_send_msgs

aps = AsyncIOScheduler(timezone="Asia/Shanghai")


class CustomLogHandler(LoguruHandler):
    def filter(self, record: logging.LogRecord):
        return record.msg != (
            'Execution of job "%s" '
            "skipped: maximum number of running instances reached (%d)"
        )


if plugin_config.bison_use_queue:
    aps.add_job(do_send_msgs, "interval", seconds=0.3, coalesce=True)

    aps_logger = logging.getLogger("apscheduler")
    aps_logger.setLevel(30)
    aps_logger.handlers.clear()
    aps_logger.addHandler(CustomLogHandler())


def start_scheduler():
    aps.configure({"apscheduler.timezone": "Asia/Shanghai"})
    aps.start()
