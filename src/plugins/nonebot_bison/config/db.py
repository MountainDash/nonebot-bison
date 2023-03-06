import json
import time
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path

from nonebot.log import logger
from nonebot_bison.types import Category, Tag
from nonebot_plugin_datastore.db import get_engine
from objtyping import to_primitive
from sqlalchemy.ext.asyncio.session import AsyncSession

from .config_legacy import ConfigContent
from .config_legacy import config as db_config_legacy
from .config_legacy import drop
from .db_config import SubscribeDupException
from .db_config import config as db_config
from .db_model import Subscribe, Target, User


async def data_migrate():
    if db_config_legacy.available:
        logger.warning("You are still using legacy db, migrating to sqlite")
        all_subs: list[ConfigContent] = list(
            map(
                lambda item: ConfigContent(**item),
                db_config_legacy.get_all_subscribe().all(),
            )
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


async def subscribes_export(export_path: Path = Path.cwd() / "data"):
    """
    bison订阅信息导出函数，生成可以导入另一个bison的订阅记录文件

    导出文件名:
        bison_subscribes_export_<导出时的时间戳>.json

    参数:
        export_path (Path, Optional): 文件的导出位置，默认为工作路径下的data文件夹

    """

    # 将数据库查询记录转换为python数据类型，并排除主键和外键
    raw_subs = to_primitive(
        await db_config.list_subs_with_all_info(),
        ignores=["id", "target_id", "user_id"],
    )
    assert isinstance(raw_subs, list)

    # 将相同user的订阅合并
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

    # 写入文件
    try:
        assert export_path.exists()
    except AssertionError:
        export_path.mkdir()
    finally:
        with open(
            export_path / f"bison_subscribes_export_{int(time.time())}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(formatted_subs, f, ensure_ascii=False, indent=4)


async def subscribes_import(import_file_path: Path):
    """
    bison订阅信息导入函数，将bison订阅导出文件导入bison中

    参数:
        import_file_path (Path, optional): 需要导入的订阅文件的位置。
    """

    @dataclass
    class ItemModel:
        user: int
        user_type: str
        target: str
        target_name: str
        platform_name: str
        categories: list[Category]
        tags: list[Tag]
        # default_schedule_weight: int

    # 合法性检查与订阅包生成
    assert import_file_path.is_file()

    with import_file_path.open(encoding="utf-8") as f:
        import_items: list[
            dict[
                str,
                dict[str, str | int]
                | list[dict[str, list[Category] | list[Tag] | dict[str, str | int]]],
            ]
        ] = json.load(f)

    assert isinstance(import_items, list)

    try:
        sub_packs: list[ItemModel] = list()
        for item in import_items:

            assert isinstance(item, dict)
            assert set(item.keys()) == {"user", "subs"}
            assert isinstance(item["user"], dict)
            assert set(item["user"].keys()) == {"type", "uid"}
            assert isinstance(item["subs"], list)

            user = item["user"]
            subs_payload = partial(ItemModel, user=user["uid"], user_type=user["type"])

            for sub in item["subs"]:

                assert isinstance(sub, dict)
                assert set(sub.keys()) == {"categois", "tags", "target"}
                assert isinstance(sub["target"], dict)
                assert set(sub["target"].keys()) == {
                    "target_name",
                    "target",
                    "platform_name",
                    "default_schedule_weight",
                }

                target = sub["target"]

                sub_pack = subs_payload(
                    categories=sub["categories"],
                    tags=sub["tags"],
                    target=target["target"],
                    target_name=target["target_name"],
                    platfrom_name=target["platform_name"],
                )
                sub_packs.append(sub_pack)

    except AssertionError as e:
        logger.error(f"！订阅该订阅记录格式非法：{repr(e)}, 终止！")
        is_check_pass = False
    except Exception as e:
        logger.error(f"！订阅文件检查异常：{repr(e)}")
        is_check_pass = False
    else:
        logger.success("订阅文件检查通过！")
        is_check_pass = True

    # 逐个添加订阅
    logger.info("检查结束，开始添加订阅流程")

    if is_check_pass:

        for sub_pack in sub_packs:

            try:
                await db_config.add_subscribe(**asdict(sub_pack))
            except SubscribeDupException:
                logger.warning(f"添加订阅条目 {repr(sub_pack)} 失败: 相同的订阅已存在")
            except Exception as e:
                logger.error(f"添加订阅条目 {repr(sub_pack)} 失败: {repr(e)}")
            else:
                logger.success(f"添加订阅条目 {repr(sub_pack)} 成功！")

        logger.info("订阅流程结束，请检查所有订阅记录是否全部添加成功")

    else:
        logger.error("订阅记录检查未通过，该订阅文件不会被导入")
