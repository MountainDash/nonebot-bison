import pytest


async def test_migration(use_legacy_config, db_migration):
    from nonebot_bison.config.config_legacy import config as config_legacy
    from nonebot_bison.config.db import data_migrate
