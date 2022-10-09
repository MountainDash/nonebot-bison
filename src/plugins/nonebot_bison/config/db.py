from pathlib import Path

from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script.base import ScriptDirectory
from nonebot.log import logger
from nonebot_plugin_datastore import PluginData, db
from nonebot_plugin_datastore.db import get_engine
from sqlalchemy.engine.base import Connection
from sqlalchemy.ext.asyncio.session import AsyncSession

from .config_legacy import ConfigContent, config, drop
from .db_model import Base, Subscribe, Target, User

DATA = PluginData("bison")


async def data_migrate():
    if config.available:
        logger.warning("You are still using legacy db, migrating to sqlite")
        all_subs: list[ConfigContent] = list(
            map(lambda item: ConfigContent(**item), config.get_all_subscribe().all())
        )
        async with AsyncSession(get_engine()) as sess:
            user_to_create = []
            subscribe_to_create = []
            platform_target_map: dict[str, tuple[Target, str, int]] = {}
            for user in all_subs:
                db_user = User(uid=user["user"], type=user["user_type"])
                user_to_create.append(db_user)
                user_sub_set = set()
                for sub in user["subs"]:
                    target = sub["target"]
                    platform_name = sub["target_type"]
                    target_name = sub["target_name"]
                    key = f"{target}-{platform_name}"
                    if key in user_sub_set:
                        # a user subscribe a target twice
                        logger.error(
                            f"用户 {user['user_type']}-{user['user']} 订阅了 {platform_name}-{target_name} 两次，"
                            "随机采用了一个订阅"
                        )
                        continue
                    user_sub_set.add(key)
                    if key in platform_target_map.keys():
                        target_obj, ext_user_type, ext_user = platform_target_map[key]
                        if target_obj.target_name != target_name:
                            # GG
                            logger.error(
                                f"你的旧版本数据库中存在数据不一致问题，请完成迁移后执行重新添加{platform_name}平台的{target}"
                                f"它的名字可能为{target_obj.target_name}或{target_name}"
                            )

                    else:
                        target_obj = Target(
                            platform_name=platform_name,
                            target_name=target_name,
                            target=target,
                        )
                        platform_target_map[key] = (
                            target_obj,
                            user["user_type"],
                            user["user"],
                        )
                    subscribe_obj = Subscribe(
                        user=db_user,
                        target=target_obj,
                        categories=sub["cats"],
                        tags=sub["tags"],
                    )
                    subscribe_to_create.append(subscribe_obj)
            sess.add_all(
                user_to_create
                + list(map(lambda x: x[0], platform_target_map.values()))
                + subscribe_to_create
            )
            await sess.commit()
            drop()
            logger.info("migrate success")


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
        env.configure(
            connection,
            target_metadata=Base.metadata,
            fn=migrate_fun,
            render_as_batch=True,
        )
        with env.begin_transaction():
            env.run_migrations()
        logger.info("Finish auto migrate")

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migration)

    await data_migrate()
