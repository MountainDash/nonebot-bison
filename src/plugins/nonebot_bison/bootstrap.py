from nonebot import get_driver
from nonebot.log import logger

from .config.config_legacy import start_up as legacy_db_startup
from .config.db import upgrade_db
from .scheduler.aps import start_scheduler
from .scheduler.manager import init_scheduler


@get_driver().on_startup
async def bootstrap():
    # legacy db
    legacy_db_startup()
    # new db
    await upgrade_db()
    # init scheduler
    await init_scheduler()
    # start scheduler
    start_scheduler()
    logger.info("nonebot-bison bootstrap done")
