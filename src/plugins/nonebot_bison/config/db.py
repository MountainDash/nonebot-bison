from pathlib import Path

import nonebot
from alembic import command
from alembic.config import Config
from nonebot_plugin_datastore import PluginData, create_session, db

DATA = PluginData("bison")


@nonebot.get_driver().on_startup
async def upgrade_db():
    alembic_cfg = Config()
    alembic_cfg.set_main_option(
        "script_location", str(Path(__file__).parent.joinpath("migrate"))
    )
    alembic_cfg.set_main_option("sqlalchemy.url", "")
    command.upgrade(alembic_cfg, "head")
