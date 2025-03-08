from collections import defaultdict
from collections.abc import Callable
from typing import cast

from nonebot.compat import type_validate_python
from nonebot.log import logger
from nonebot_plugin_datastore.db import create_session
from nonebot_plugin_saa import PlatformTarget
from sqlalchemy import select
from sqlalchemy.orm.strategy_options import selectinload
from sqlalchemy.sql.selectable import Select

from nonebot_bison.config import config
from nonebot_bison.config.db_model import Cookie, CookieTarget, Subscribe, Target, User

from .nbesf_model import NBESFBase, v1, v2, v3
from .utils import NBESFVerMatchErr, row2dict


async def subscribes_export(selector: Callable[[Select], Select]) -> v3.SubGroup:
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

    groups: list[v3.SubPack] = []
    user_id_sub_dict: dict[int, list[v3.SubPayload]] = defaultdict(list)

    for sub in sub_data:
        sub_paylaod = type_validate_python(v3.SubPayload, sub)
        user_id_sub_dict[sub.user_id].append(sub_paylaod)

    for user in user_data:
        assert isinstance(user, User)
        sub_pack = v3.SubPack(
            user_target=PlatformTarget.deserialize(user.user_target),
            subs=user_id_sub_dict[user.id],
        )
        groups.append(sub_pack)

    async with create_session() as sess:
        cookie_target_stmt = (
            select(CookieTarget)
            .join(Cookie)
            .join(Target)
            .options(selectinload(CookieTarget.target))
            .options(selectinload(CookieTarget.cookie))
        )
        cookie_target_data = await sess.scalars(cookie_target_stmt)

    cookie_target_dict: dict[Cookie, list[v3.Target]] = defaultdict(list)
    for cookie_target in cookie_target_data:
        target_payload = type_validate_python(v3.Target, cookie_target.target)
        cookie_target_dict[cookie_target.cookie].append(target_payload)

    def cookie_transform(cookie: Cookie, targets: list[v3.Target]) -> v3.Cookie:
        cookie_dict = row2dict(cookie)
        cookie_dict["tags"] = cookie.tags
        cookie_dict["targets"] = targets
        return v3.Cookie(**cookie_dict)

    cookies: list[v3.Cookie] = []
    cookie_set = set()
    for cookie, targets in cookie_target_dict.items():
        assert isinstance(cookie, Cookie)
        cookies.append(cookie_transform(cookie, targets))
        cookie_set.add(cookie.id)

    # 添加未关联的cookie
    all_cookies = await config.get_cookie(is_anonymous=False)
    cookies.extend([cookie_transform(c, []) for c in all_cookies if c.id not in cookie_set])

    sub_group = v3.SubGroup(groups=groups, cookies=cookies)

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
        case 3:
            assert isinstance(nbesf_data, v3.SubGroup)
            await v3.subs_receipt_gen(nbesf_data)
            await v3.magic_cookie_gen(nbesf_data)
        case _:
            raise NBESFVerMatchErr(f"不支持的NBESF版本：{nbesf_data.version}")
    logger.info("订阅流程结束，请检查所有订阅记录是否全部添加成功")
