from nonebot.log import logger
from sqlalchemy import text, inspect
from nonebot_plugin_datastore.db import get_engine, pre_db_init, post_db_init

from .config.db_migration import data_migrate
from .scheduler.manager import init_scheduler
from .config.config_legacy import start_up as legacy_db_startup


@pre_db_init
async def pre():
    def _has_table(conn, table_name):
        insp = inspect(conn)
        return insp.has_table(table_name)

    async with get_engine().begin() as conn:
        if not await conn.run_sync(_has_table, "alembic_version"):
            logger.debug("未发现默认版本数据库，开始初始化")
            return

        logger.debug("发现默认版本数据库，开始检查版本")
        t = await conn.scalar(text("select version_num from alembic_version"))
        if t not in [
            "4a46ba54a3f3",  # alter_type
            "5f3370328e44",  # add_time_weight_table
            "0571870f5222",  # init_db
            "a333d6224193",  # add_last_scheduled_time
            "c97c445e2bdb",  # add_constraint
        ]:
            logger.warning(f"当前数据库版本：{t}，不是插件的版本，已跳过。")
            return

        logger.debug(f"当前数据库版本：{t}，是插件的版本，开始迁移。")
        # 删除可能存在的版本数据库
        if await conn.run_sync(_has_table, "nonebot_bison_alembic_version"):
            await conn.execute(text("drop table nonebot_bison_alembic_version"))

        await conn.execute(text("alter table alembic_version rename to nonebot_bison_alembic_version"))


@post_db_init
async def post():
    # legacy db
    legacy_db_startup()
    # migrate data
    await data_migrate()
    # init scheduler
    await init_scheduler()
    logger.info("nonebot-bison bootstrap done")
