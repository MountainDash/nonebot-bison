import json
import time
from dataclasses import asdict
from functools import partial
from pathlib import Path
from typing import Any, Callable, Coroutine, ParamSpecArgs, ParamSpecKwargs, Sequence

from nonebot.log import logger
from objtyping import to_primitive

from nonebot_bison.config.db_model import Subscribe

from ...config.db_config import SubscribeDupException
from ...config.db_config import config as db_config
from ...types import Category, Tag
from ...types import Target as T_Target
from .nbesf_model import ItemModel, PackAsNBESF, SubGroup, SubPack, SubPayload, UserHead


async def subscribes_export(
    fetcher_func: Callable[..., Coroutine[Any, Any, Sequence[Subscribe]]]
) -> SubGroup:

    db_data_seq = await fetcher_func()

    user_set: set[UserHead] = set()
    groups: list[SubPack] = []
    for item in db_data_seq:

        checking_user = UserHead.from_orm(item.user)
        new_sub_payload = SubPayload.from_orm(item)

        if checking_user in user_set:
            # 已有收货信息？向包裹追加货物！
            for existing_sub_pack in groups:
                if checking_user == existing_sub_pack.user:
                    existing_sub_pack.subs.append(new_sub_payload)
                    break
        else:
            # 新的收货信息？创建新的包裹！
            user_set.add(checking_user)
            new_sub_pack = SubPack(user=checking_user, subs=[new_sub_payload])
            groups.append(new_sub_pack)

    sub_group = PackAsNBESF(groups=groups)

    return sub_group


class SubsImport:
    def __init__(
        self,
        func: Callable[
            ...,
            Coroutine[Any, Any, Any],
        ],
    ):
        """
        func:
            可以导入订阅记录的数据库导入函数
        """
        self.dump_db_data_hook = func

    def check_and_build(self):
        """检查导入数据结构并构建导入包

        注意：
            只要数据有任何非法部分，订阅将不会开始
        """
        assert self.import_items, "请先导入文件！"

        logger.info("文件内容结构合法性检测与构建开始...")
        assert isinstance(self.import_items, list), "读取的结构不是list类型！"

        sub_packs: list[ItemModel] = list()
        try:
            for item in self.import_items:

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
                subs_payload = partial(
                    ItemModel, user=user["uid"], user_type=user["type"]
                )

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
            self.is_check_pass = False
            self.sub_packs = list()
            return False
        except Exception as e:
            logger.error(f"！订阅文件检查异常：{e}")
            self.is_check_pass = False
            self.sub_packs = list()
            return False
        else:
            logger.success("订阅文件检查通过！")
            self.is_check_pass = True
            self.sub_packs: list[ItemModel] = sub_packs
            return True

    async def dump_in(self):
        """将生成的订阅包加入数据库"""

        # 逐个添加订阅
        logger.info("开始添加订阅流程")

        if self.is_check_pass:

            assert self.sub_packs, "请先使用 check_and_build 函数构建订阅包"
            assert self.dump_db_data_hook

            for sub_pack in self.sub_packs:

                try:
                    await self.dump_db_data_hook(**asdict(sub_pack))  # type: ignore
                except SubscribeDupException:
                    logger.warning(f"！添加订阅条目 {repr(sub_pack)} 失败: 相同的订阅已存在")
                except Exception as e:
                    logger.error(f"！添加订阅条目 {repr(sub_pack)} 失败: {repr(e)}")
                else:
                    logger.success(f"添加订阅条目 {repr(sub_pack)} 成功！")

            logger.info("订阅流程结束，请检查所有订阅记录是否全部添加成功")

        else:
            logger.error("订阅记录检查未通过，该订阅文件不会被导入")

    def load_from(self, import_items: list[dict]):
        """
        bison订阅信息数据导入函数，将bison订阅数据导入bison中

        格式请参考本子模块下的nbesf_model.py里定义的类所对应dict格式!

        参数:
            import_items (nbesf结构): 需要导入的订阅文件的位置。
        """
        self.import_items = import_items

        return self.check_and_build()

    def import_from(self, import_file_path: Path):
        """
        bison订阅信息文件导入函数，将bison订阅导出文件导入bison中

        参数:
            import_file_path (Path, optional): 需要导入的订阅文件的位置。
        """
        # 合法性检查与订阅包生成
        assert import_file_path.is_file()
        logger.success(f"文件 {import_file_path} 存在，继续流程")

        with import_file_path.open(encoding="utf-8") as f:
            self.import_items = json.load(f)

        return self.check_and_build()


subscribes_import = SubsImport(db_config.add_subscribe)
