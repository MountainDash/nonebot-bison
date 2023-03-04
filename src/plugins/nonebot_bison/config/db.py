import json
import time
from pathlib import Path

from nonebot.log import logger
from nonebot_plugin_datastore.db import get_engine
from objtyping import to_primitive
from sqlalchemy.ext.asyncio.session import AsyncSession

from .config_legacy import ConfigContent, config, drop
from .db_config import config as db_config
from .db_model import Subscribe, Target, User


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


async def subscribes_export():
    """bison订阅信息导出函数，生成可以导入另一个bison的订阅记录文件"""

    # 将数据库查询记录转换为python数据类型，并排除主键和外键
    raw_subs = to_primitive(
        db_config.list_subs_with_all_info(), ignores=["id", "target_id", "user_id"]
    )
    assert isinstance(raw_subs, list)

    formatted_subs = []
    users = set()

    for sub in raw_subs:
        assert isinstance(sub, dict)
        user = sub["user"]

        if user["uid"] in users:
            # 已有该user，追加记录到该user下的subs
            for item in formatted_subs:

                if item["user"] == user:
                    new_sub = sub.copy()
                    new_sub.pop("user")
                    item["subs"].append(new_sub)

                    break

        else:
            # 新的user，新建该user的订阅信息
            users.add(user["uid"])
            subs = []

            new_sub = sub.copy()
            new_sub.pop("user")
            subs.append(new_sub)

            formatted_subs.append({"user": user, "subs": subs})

    export_path = Path.cwd() / "data"
    try:
        assert export_path.exists()
    except AssertionError:
        export_path.mkdir(666)
    finally:
        with open(
            export_path / f"subscribes_export_{int(time.time())}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(formatted_subs, f, ensure_ascii=False, indent=4)
