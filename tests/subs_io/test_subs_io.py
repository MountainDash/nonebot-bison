from pathlib import Path

import pytest
from nonebug.app import App

from .utils import get_file, get_json


async def test_subs_export(app: App, init_scheduler):
    import time

    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.db_model import User
    from nonebot_bison.config.subs_io import subscribes_export
    from nonebot_bison.types import Target as TTarget

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        user=234,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=["kaltsit", "amiya"],
    )
    await config.add_subscribe(
        user=234,
        user_type="group",
        target=TTarget("bilibili_id"),
        target_name="bilibili_name",
        platform_name="bilibili",
        cats=[1, 2],
        tags=[],
    )

    data = await config.list_subs_with_all_info()
    assert len(data) == 3

    nbesf_data = await subscribes_export(lambda x: x)
    assert nbesf_data.dict() == get_json("subs_export.json")

    nbesf_data_user_234 = await subscribes_export(
        lambda stmt: stmt.where(User.uid == 234, User.type == "group")
    )
    assert len(nbesf_data_user_234.groups) == 1
    assert len(nbesf_data_user_234.groups[0].subs) == 2
    assert nbesf_data_user_234.groups[0].user.dict() == {"uid": 234, "type": "group"}


async def test_subs_import(app: App, init_scheduler):
    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.subs_io import nbesf_parser, subscribes_import

    nbesf_data = nbesf_parser(get_json("subs_export.json"))

    await subscribes_import(nbesf_data)

    data = await config.list_subs_with_all_info()
    assert len(data) == 3


async def test_subs_import_dup_err(app: App, init_scheduler):

    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.subs_io import nbesf_parser, subscribes_import

    nbesf_data = nbesf_parser(get_json("subs_export_has_subdup_err.json"))

    await subscribes_import(nbesf_data)

    data = await config.list_subs_with_all_info()

    assert len(data) == 4


async def test_subs_import_all_fail(app: App, init_scheduler):
    """只要文件格式有任何一个错误， 都不会进行订阅"""
    from nonebot_bison.config.subs_io import nbesf_parser
    from nonebot_bison.config.subs_io.nbesf_model import NBESFParseErr

    with pytest.raises(NBESFParseErr):
        nbesf_data = nbesf_parser(get_json("subs_export_all_illegal.json"))
