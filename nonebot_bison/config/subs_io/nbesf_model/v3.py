"""nbesf is Nonebot Bison Enchangable Subscribes File! ver.2"""

from functools import partial
from typing import Any

from nonebot.compat import PYDANTIC_V2, ConfigDict, model_dump, type_validate_json, type_validate_python
from nonebot.log import logger
from nonebot_plugin_saa.registries import AllSupportedPlatformTarget
from pydantic import BaseModel, Field

from nonebot_bison.config.db_config import SubscribeDupException, config
from nonebot_bison.config.db_model import Cookie as DBCookie
from nonebot_bison.config.subs_io.utils import NBESFParseErr
from nonebot_bison.types import Category, Tag
from nonebot_bison.types import Target as T_Target

from .base import NBESFBase, SubReceipt

# ===== nbesf 定义格式 ====== #
NBESF_VERSION = 3


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


class Cookie(BaseModel):
    """Bison的魔法饼干"""

    site_name: str
    content: str
    cookie_name: str
    cd_milliseconds: int
    is_universal: bool
    tags: dict[str, str]
    targets: list[Target]


class SubPack(BaseModel):
    """Bison给指定用户派送的快递包"""

    # user_target: Bison快递包收货信息
    user_target: AllSupportedPlatformTarget
    subs: list[SubPayload]


class SubGroup(NBESFBase):
    """
    Bison的全部订单(按用户分组)和魔法饼干

    结构参见`nbesf_model`下的对应版本
    """

    version: int = NBESF_VERSION
    groups: list[SubPack] = Field(default_factory=list)
    cookies: list[Cookie] = Field(default_factory=list)


# ======================= #


async def subs_receipt_gen(nbesf_data: SubGroup):
    logger.info("开始添加订阅流程")
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
                logger.warning(f"！添加订阅条目 {receipt!r} 失败: 相同的订阅已存在")
            except Exception as e:
                logger.error(f"！添加订阅条目 {receipt!r} 失败: {e!r}")
            else:
                logger.success(f"添加订阅条目 {receipt!r} 成功！")


async def magic_cookie_gen(nbesf_data: SubGroup):
    logger.info("开始添加 Cookie 流程")
    for cookie in nbesf_data.cookies:
        try:
            new_cookie = DBCookie(**model_dump(cookie, exclude={"targets"}))
            cookie_id = await config.add_cookie(new_cookie)
            for target in cookie.targets:
                await config.add_cookie_target(T_Target(target.target), target.platform_name, cookie_id)
        except Exception as e:
            logger.error(f"！添加 Cookie 条目 {cookie!r} 失败: {e!r}")
        else:
            logger.success(f"添加 Cookie 条目 {cookie!r} 成功！")


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
