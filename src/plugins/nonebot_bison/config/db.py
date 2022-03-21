from pathlib import Path

import nonebot
from alembic import command
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script.base import ScriptDirectory
from nonebot_plugin_datastore import PluginData, create_session, db

from .db_model import Base

DATA = PluginData("bison")


@nonebot.get_driver().on_startup
async def upgrade_db():
    alembic_cfg = Config()
    alembic_cfg.set_main_option(
        "script_location", str(Path(__file__).parent.joinpath("migrate"))
    )
    alembic_cfg.set_main_option("sqlalchemy.url", "")
    command.upgrade(alembic_cfg, "head")

    script = ScriptDirectory.from_config(alembic_cfg)

    def upgrade(rev, context):
        return script._upgrade_revs("head", rev)

    with EnvironmentContext(
        alembic_cfg,
        script,
        fn=upgrade,
        as_sql=False,
        starting_rev=None,
        destination_rev="head",
        tag=None,
        target_metadata=Base.metadata,
    ):
        script.run_env()
