import json
import time
from dataclasses import asdict
from functools import partial
from pathlib import Path

from nonebot.log import logger
from objtyping import to_primitive

from ..config.db_config import SubscribeDupException
from ..config.db_config import config as db_config
from ..types import Category, Tag
from .nbesf_model import ItemModel


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
    # 合法性检查与订阅包生成
    assert import_file_path.is_file()
    logger.success(f"文件 {import_file_path} 存在，继续流程")

    with import_file_path.open(encoding="utf-8") as f:
        import_items: list[
            dict[
                str,
                dict[str, str | int]
                | list[dict[str, list[Category] | list[Tag] | dict[str, str | int]]],
            ]
        ] = json.load(f)

    logger.info("文件内容结构合法性检测开始...")
    assert isinstance(import_items, list), "读取的结构不是list类型！"

    sub_packs: list[ItemModel] = list()
    try:
        for item in import_items:

            assert isinstance(item, dict)
            assert set(item.keys()) == {"user", "subs"}, (
                "第一层键名与 user, subs 不匹配！",
                item,
            )
            assert isinstance(item["user"], dict), ("user字段不是dict类型！", item["user"])
            assert set(item["user"].keys()) == {"type", "uid"}, (
                "user字段键名与 type, uid 不匹配！",
                item["user"],
            )
            assert isinstance(item["subs"], list), ("subs字段不是list类型！", item["user"])

            user = item["user"]
            subs_payload = partial(ItemModel, user=user["uid"], user_type=user["type"])

            for sub in item["subs"]:

                assert isinstance(sub, dict), ("subs list中存在非dict类型！", sub)
                assert set(sub.keys()) == {"categories", "tags", "target"}, (
                    "subs list元素含有的键名与 categories, tags, target 不匹配！",
                    sub,
                )
                assert isinstance(sub["target"], dict), (
                    "target字段不是dict类型",
                    sub["target"],
                )
                assert set(sub["target"].keys()) == {
                    "target_name",
                    "target",
                    "platform_name",
                    "default_schedule_weight",
                }, (
                    "target字段键名与 target_name, target, platform_name, default_schedule_weight 不匹配！",
                    sub["target"],
                )

                target = sub["target"]

                sub_pack = subs_payload(
                    cats=sub["categories"],
                    tags=sub["tags"],
                    target=target["target"],
                    target_name=target["target_name"],
                    platform_name=target["platform_name"],
                )
                sub_packs.append(sub_pack)

    except AssertionError as e:
        logger.error(f"！订阅该订阅记录格式非法：{e.args[0][0]}, 终止！")
        logger.error(f"错误订阅数据:{e.args[0][1]}")
        is_check_pass = False
    except Exception as e:
        logger.error(f"！订阅文件检查异常：{e}")
        is_check_pass = False
    else:
        logger.success("订阅文件检查通过！")
        is_check_pass = True

    # 逐个添加订阅
    logger.info("检查结束，开始添加订阅流程")

    if is_check_pass and sub_packs:

        for sub_pack in sub_packs:

            try:
                await db_config.add_subscribe(**asdict(sub_pack))
            except SubscribeDupException:
                logger.warning(f"！添加订阅条目 {repr(sub_pack)} 失败: 相同的订阅已存在")
            except Exception as e:
                logger.error(f"！添加订阅条目 {repr(sub_pack)} 失败: {repr(e)}")
            else:
                logger.success(f"添加订阅条目 {repr(sub_pack)} 成功！")

        logger.info("订阅流程结束，请检查所有订阅记录是否全部添加成功")

    else:
        logger.error("订阅记录检查未通过，该订阅文件不会被导入")
