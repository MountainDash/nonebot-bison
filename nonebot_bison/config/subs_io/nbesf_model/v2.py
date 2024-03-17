"""nbesf is Nonebot Bison Enchangable Subscribes File! ver.2"""

from typing import Any
from functools import partial

from nonebot.log import logger
from pydantic import BaseModel
from nonebot_plugin_saa.registries import AllSupportedPlatformTarget
from nonebot.compat import PYDANTIC_V2, ConfigDict, model_dump, type_validate_json, type_validate_python

from ..utils import NBESFParseErr
from ....types import Tag, Category
from .base import NBESFBase, SubReceipt
from ...db_config import SubscribeDupException, config

# ===== nbesf 定义格式 ====== #
NBESF_VERSION = 2


class Target(BaseModel):
    """Bsion快递包发货信息"""

    target_name: str
    target: str
    platform_name: str
    default_schedule_weight: int

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:

        class Config:
            orm_mode = True


class SubPayload(BaseModel):
    """Bison快递包里的单件货物"""

    categories: list[Category]
    tags: list[Tag]
    target: Target

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:

        class Config:
            orm_mode = True


class SubPack(BaseModel):
    """Bison给指定用户派送的快递包"""

    # user_target: Bison快递包收货信息
    user_target: AllSupportedPlatformTarget
    subs: list[SubPayload]


class SubGroup(NBESFBase):
    """
    Bison的全部订单(按用户分组)

    结构参见`nbesf_model`下的对应版本
    """

    version: int = NBESF_VERSION
    groups: list[SubPack]


# ======================= #


async def subs_receipt_gen(nbesf_data: SubGroup):
    for item in nbesf_data.groups:
        sub_receipt = partial(SubReceipt, user=item.user_target)

        for sub in item.subs:
            receipt = sub_receipt(
                target=sub.target.target,
                target_name=sub.target.target_name,
                platform_name=sub.target.platform_name,
                cats=sub.categories,
                tags=sub.tags,
            )
            try:
                await config.add_subscribe(receipt.user, **model_dump(receipt, exclude={"user"}))
            except SubscribeDupException:
                logger.warning(f"！添加订阅条目 {repr(receipt)} 失败: 相同的订阅已存在")
            except Exception as e:
                logger.error(f"！添加订阅条目 {repr(receipt)} 失败: {repr(e)}")
            else:
                logger.success(f"添加订阅条目 {repr(receipt)} 成功！")


def nbesf_parser(raw_data: Any) -> SubGroup:
    try:
        if isinstance(raw_data, str):
            nbesf_data = type_validate_json(SubGroup, raw_data)
        else:
            nbesf_data = type_validate_python(SubGroup, raw_data)

    except Exception as e:
        logger.error("数据解析失败，该数据格式可能不满足NBESF格式标准！")
        raise NBESFParseErr("数据解析失败") from e
    else:
        return nbesf_data
