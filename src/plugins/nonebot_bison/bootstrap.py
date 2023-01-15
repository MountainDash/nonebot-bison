from nonebot.log import logger
from nonebot_plugin_datastore import create_session
from nonebot_plugin_datastore.db import post_db_init, pre_db_init
from sqlmodel import text

from .config.config_legacy import start_up as legacy_db_startup
from .config.db import data_migrate
from .scheduler.aps import start_scheduler
from .scheduler.manager import init_scheduler


@pre_db_init
async def pre():
    async with create_session() as session:
        t = text(
            """ALTER TABLE alembic_version RENAME TO nonebot_bison_alembic_version;"""
        )
        try:
            await session.execute(t)
        except:
            pass


@post_db_init
async def post():
    # legacy db
    legacy_db_startup()
    # migrate data
    await data_migrate()
    # init scheduler
    await init_scheduler()
    # start scheduler
    start_scheduler()
    logger.info("nonebot-bison bootstrap done")
