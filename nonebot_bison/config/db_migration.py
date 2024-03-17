from nonebot.log import logger
from nonebot.compat import model_dump
from nonebot_plugin_datastore.db import get_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from nonebot_plugin_saa import TargetQQGroup, TargetQQPrivate

from .db_model import User, Target, Subscribe
from .config_legacy import Config, ConfigContent, drop


async def data_migrate():
    config = Config()
    if config.available:
        logger.warning("You are still using legacy db, migrating to sqlite")
        all_subs: list[ConfigContent] = [ConfigContent(**item) for item in config.get_all_subscribe().all()]
        async with AsyncSession(get_engine()) as sess:
            user_to_create = []
            subscribe_to_create = []
            platform_target_map: dict[str, tuple[Target, str, int]] = {}
            for user in all_subs:
                if user["user_type"] == "group":
                    user_target = TargetQQGroup(group_id=user["user"])
                else:
                    user_target = TargetQQPrivate(user_id=user["user"])
                db_user = User(user_target=model_dump(user_target))
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
                            "随机采用了一个订阅",
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
            sess.add_all(user_to_create + [x[0] for x in platform_target_map.values()] + subscribe_to_create)
            await sess.commit()
            drop()
            logger.info("migrate success")
