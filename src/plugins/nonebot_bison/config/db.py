from pathlib import Path

import nonebot
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script.base import ScriptDirectory
from nonebot.log import logger
from nonebot_plugin_datastore import PluginData, create_session, db
from sqlalchemy.engine.base import Connection

from .config_legacy import ConfigContent, config
from .db_model import Base

DATA = PluginData("bison")


async def data_migrate():
    if config.available:
        logger.warning("You are still using legacy db, migrating to sqlite")
        all_subs: list[ConfigContent] = list(
            map(lambda item: ConfigContent(**item), config.get_all_subscribe().all())
        )


@nonebot.get_driver().on_startup
async def upgrade_db():
    alembic_cfg = Config()
    alembic_cfg.set_main_option(
        "script_location", str(Path(__file__).parent.joinpath("migrate"))
    )

    script = ScriptDirectory.from_config(alembic_cfg)
    engine = db.get_engine()
    env = EnvironmentContext(alembic_cfg, script)

    def migrate_fun(revision, context):
        return script._upgrade_revs("head", revision)

    def do_run_migration(connection: Connection):
        env.configure(connection, target_metadata=Base.metadata, fn=migrate_fun)
        with env.begin_transaction():
            env.run_migrations()
        logger.info("Finish auto migrate")

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migration)

    await data_migrate()
