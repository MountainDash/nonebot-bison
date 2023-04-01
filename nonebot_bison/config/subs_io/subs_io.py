from collections import defaultdict
from typing import Any, Callable, cast

from nonebot.log import logger
from nonebot_plugin_datastore.db import create_session
from sqlalchemy import select
from sqlalchemy.orm.strategy_options import selectinload
from sqlalchemy.sql.selectable import Select

from ..db_model import Subscribe, User
from .nbesf_model import (
    NBESFParseErr,
    NBESFVerMatchErr,
    SubGroup,
    SubPack,
    SubPayload,
    UserHead,
)
from .utils import subs_receipt_gen_ver_1


async def subscribes_export(selector: Callable[[Select], Select]) -> SubGroup:
    """
    将Bison订阅导出为 Nonebot Bison Exchangable Subscribes File 标准格式的 SubGroup 类型数据

    selector:
        对 sqlalchemy Select 对象的操作函数，用于限定查询范围 e.g. lambda stmt: stmt.where(User.uid=2233, User.type="group")
    """
    async with create_session() as sess:
        sub_stmt = select(Subscribe).join(User)
        sub_stmt = selector(sub_stmt).options(selectinload(Subscribe.target))
        sub_stmt = cast(Select[tuple[Subscribe]], sub_stmt)
        sub_data = await sess.scalars(sub_stmt)

        user_stmt = select(User).join(Subscribe)
        user_stmt = selector(user_stmt).distinct()
        user_stmt = cast(Select[tuple[User]], user_stmt)
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
    nbesf_data: SubGroup,
):
    """
    从 Nonebot Bison Exchangable Subscribes File 标准格式的数据中导入订阅

    nbesf_data:
        符合nbesf_model标准的 SubGroup 类型数据
    """

    logger.info("开始添加订阅流程")
    match nbesf_data.version:
        case 1:
            await subs_receipt_gen_ver_1(nbesf_data)
        case _:
            raise NBESFVerMatchErr(f"不支持的NBESF版本：{nbesf_data.version}")
    logger.info("订阅流程结束，请检查所有订阅记录是否全部添加成功")


def nbesf_parser(raw_data: Any) -> SubGroup:
    try:
        if isinstance(raw_data, str):
            nbesf_data = SubGroup.parse_raw(raw_data)
        else:
            nbesf_data = SubGroup.parse_obj(raw_data)

    except Exception as e:
        logger.error("数据解析失败，该数据格式可能不满足NBESF格式标准！")
        raise NBESFParseErr("数据解析失败") from e
    else:
        return nbesf_data
