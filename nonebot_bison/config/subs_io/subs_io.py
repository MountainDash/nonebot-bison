from collections import defaultdict
from functools import partial
from typing import Any, Callable, Coroutine, Sequence, TypeVar

from nonebot.log import logger
from nonebot_plugin_datastore.db import create_session
from sqlalchemy import select
from sqlalchemy.orm.strategy_options import selectinload
from sqlalchemy.sql.selectable import Select

from ..db_config import SubscribeDupException
from ..db_model import Subscribe, User
from .nbesf_model import (
    NBESFParseErr,
    SubGroup,
    SubPack,
    SubPayload,
    SubReceipt,
    UserHead,
    nbesf_version_checker,
)

T = TypeVar("T", bound=Select)


async def subscribes_export(selector: Callable[[T], T]) -> SubGroup:
    """
    将Bison订阅导出为 Nonebot Bison Exchangable Subscribes File 标准格式的 SubGroup 类型数据

    selector:
        对 sqlalchemy Select 对象的操作函数，用于限定查询范围 e.g. lambda stmt: stmt.where(User.uid=2233, User.type="group")
    """
    async with create_session() as sess:
        sub_stmt = select(Subscribe).join(User)
        sub_stmt = selector(sub_stmt).options(selectinload(Subscribe.target))
        sub_data = await sess.scalars(sub_stmt)

        user_stmt = select(User).join(Subscribe)
        user_stmt = selector(user_stmt).distinct()
        user_data = await sess.scalars(user_stmt)

    groups: list[SubPack] = []
    user_id_sub_dict: dict[int, list[SubPayload]] = defaultdict(list)

    for sub in sub_data:
        sub_paylaod = SubPayload.from_orm(sub)
        user_id_sub_dict[sub.user_id].append(sub_paylaod)

    for user in user_data:
        user_head = UserHead.from_orm(user)
        sub_pack = SubPack(user=user_head, subs=user_id_sub_dict[user.id])
        groups.append(sub_pack)

    sub_group = SubGroup(groups=groups)

    return sub_group


async def subscribes_import(
    nbesf_data: SubGroup, dumpee_func: Callable[..., Coroutine[Any, Any, Any]]
):
    """
    从 Nonebot Bison Exchangable Subscribes File 标准格式的数据中导入订阅

    nbesf_data:
        符合nbesf_model标准的 SubGroup 类型数据

    dumpee_func:
        向数据库中添加订阅信息的函数
    """

    nbesf_version_checker(nbesf_data.version)

    logger.info("开始添加订阅流程")
    for item in nbesf_data.groups:
        sub_receipt = partial(SubReceipt, user=item.user.uid, user_type=item.user.type)

        for sub in item.subs:
            receipt = sub_receipt(
                target=sub.target.target,
                target_name=sub.target.target_name,
                platform_name=sub.target.platform_name,
                cats=sub.categories,
                tags=sub.tags,
            )
            try:
                await dumpee_func(**receipt.dict())
            except SubscribeDupException:
                logger.warning(f"！添加订阅条目 {repr(receipt)} 失败: 相同的订阅已存在")
            except Exception as e:
                logger.error(f"！添加订阅条目 {repr(receipt)} 失败: {repr(e)}")
            else:
                logger.success(f"添加订阅条目 {repr(receipt)} 成功！")

    logger.info("订阅流程结束，请检查所有订阅记录是否全部添加成功")


def nbesf_parser(raw_data: Any) -> SubGroup:
    try:
        nbesf_data = SubGroup.parse_obj(raw_data)
    except:
        logger.error("该数据格式不满足NBESF格式标准！")
        raise NBESFParseErr
    else:
        return nbesf_data
