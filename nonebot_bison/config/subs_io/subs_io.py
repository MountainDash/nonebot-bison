from typing import cast
from collections import defaultdict
from collections.abc import Callable

from sqlalchemy import select
from nonebot.log import logger
from sqlalchemy.sql.selectable import Select
from nonebot_plugin_saa import PlatformTarget
from nonebot.compat import type_validate_python
from nonebot_plugin_datastore.db import create_session
from sqlalchemy.orm.strategy_options import selectinload

from .utils import NBESFVerMatchErr
from ..db_model import User, Subscribe
from .nbesf_model import NBESFBase, v1, v2


async def subscribes_export(selector: Callable[[Select], Select]) -> v2.SubGroup:
    """
    将Bison订阅导出为 Nonebot Bison Exchangable Subscribes File 标准格式的 SubGroup 类型数据

    selector:
        对 sqlalchemy Select 对象的操作函数，用于限定查询范围
        e.g. lambda stmt: stmt.where(User.uid=2233, User.type="group")
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

    groups: list[v2.SubPack] = []
    user_id_sub_dict: dict[int, list[v2.SubPayload]] = defaultdict(list)

    for sub in sub_data:
        sub_paylaod = type_validate_python(v2.SubPayload, sub)
        user_id_sub_dict[sub.user_id].append(sub_paylaod)

    for user in user_data:
        assert isinstance(user, User)
        sub_pack = v2.SubPack(
            user_target=PlatformTarget.deserialize(user.user_target),
            subs=user_id_sub_dict[user.id],
        )
        groups.append(sub_pack)

    sub_group = v2.SubGroup(groups=groups)

    return sub_group


async def subscribes_import(
    nbesf_data: NBESFBase,
):
    """
    从 Nonebot Bison Exchangable Subscribes File 标准格式的数据中导入订阅

    nbesf_data:
        符合nbesf_model标准的 SubGroup 类型数据
    """

    logger.info("开始添加订阅流程")
    match nbesf_data.version:
        case 1:
            assert isinstance(nbesf_data, v1.SubGroup)
            await v1.subs_receipt_gen(nbesf_data)
        case 2:
            assert isinstance(nbesf_data, v2.SubGroup)
            await v2.subs_receipt_gen(nbesf_data)
        case _:
            raise NBESFVerMatchErr(f"不支持的NBESF版本：{nbesf_data.version}")
    logger.info("订阅流程结束，请检查所有订阅记录是否全部添加成功")
