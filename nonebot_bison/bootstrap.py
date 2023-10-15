from nonebot import get_driver
from nonebot.log import logger

from .config.db_migration import data_migrate
from .scheduler.manager import init_scheduler
from .config.config_legacy import start_up as legacy_db_startup

driver = get_driver()


@driver.on_startup
async def post():
    # legacy db
    legacy_db_startup()
    # migrate data
    await data_migrate()
    # init scheduler
    await init_scheduler()
    logger.info("nonebot-bison bootstrap done")
