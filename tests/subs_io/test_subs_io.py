from nonebot.compat import model_dump
from nonebug.app import App
import pytest

from .utils import get_json


@pytest.mark.usefixtures("_clear_db")
async def test_subs_export(app: App, init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.db_model import Cookie, User
    from nonebot_bison.config.subs_io import subscribes_export
    from nonebot_bison.types import Target as TTarget

    await config.add_subscribe(
        TargetQQGroup(group_id=1232),
        target=TTarget(TTarget("weibo_id")),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        TargetQQGroup(group_id=2342),
        target=TTarget(TTarget("weibo_id")),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=["kaltsit", "amiya"],
    )
    await config.add_subscribe(
        TargetQQGroup(group_id=2342),
        target=TTarget("bilibili_id"),
        target_name="bilibili_name",
        platform_name="bilibili",
        cats=[1, 2],
        tags=[],
    )
    cookie_id = await config.add_cookie(
        Cookie(
            site_name="weibo.com",
            content='{"cookie": "test"}',
            cookie_name="test cookie",
        )
    )
    await config.add_cookie_target(TTarget("weibo_id"), "weibo", cookie_id)

    data = await config.list_subs_with_all_info()
    assert len(data) == 3

    nbesf_data = await subscribes_export(lambda x: x)
    assert model_dump(nbesf_data) == get_json("v3/subs_export.json")

    nbesf_data_user_234 = await subscribes_export(
        lambda stmt: stmt.where(User.user_target == {"platform_type": "QQ Group", "group_id": 2342})
    )
    assert len(nbesf_data_user_234.groups) == 1
    assert len(nbesf_data_user_234.groups[0].subs) == 2
    assert model_dump(nbesf_data_user_234.groups[0].user_target) == {
        "group_id": 2342,
        "platform_type": "QQ Group",
    }


async def test_subs_import(app: App, init_scheduler):
    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.subs_io import subscribes_import
    from nonebot_bison.config.subs_io.nbesf_model import v1, v2

    # v1
    nbesf_data_v1 = v1.nbesf_parser(get_json("v1/subs_export.json"))

    await subscribes_import(nbesf_data_v1)

    data = await config.list_subs_with_all_info()
    assert len(data) == 3

    # v2
    nbesf_data_v2 = v2.nbesf_parser(get_json("v2/subs_export.json"))

    await subscribes_import(nbesf_data_v2)
    data = await config.list_subs_with_all_info()
    assert len(data) == 6


async def test_subs_import_dup_err(app: App, init_scheduler):
    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.subs_io import subscribes_import
    from nonebot_bison.config.subs_io.nbesf_model import v1, v2

    # v1
    nbesf_data_v1 = v1.nbesf_parser(get_json("v1/subs_export_has_subdup_err.json"))

    await subscribes_import(nbesf_data_v1)

    data = await config.list_subs_with_all_info()

    assert len(data) == 4

    # v2
    nbesf_data_v2 = v2.nbesf_parser(get_json("v2/subs_export_has_subdup_err.json"))

    await subscribes_import(nbesf_data_v2)

    data = await config.list_subs_with_all_info()

    assert len(data) == 8


async def test_subs_import_version_disorder(app: App, init_scheduler):
    from nonebot_bison.config.subs_io import subscribes_import
    from nonebot_bison.config.subs_io.nbesf_model import v1, v2, v3
    from nonebot_bison.config.subs_io.utils import NBESFParseErr

    # use v1 parse v2
    with pytest.raises(NBESFParseErr):
        v1.nbesf_parser(get_json("v2/subs_export_has_subdup_err.json"))
    # use v1 parse v3
    with pytest.raises(NBESFParseErr):
        v1.nbesf_parser(get_json("v3/subs_export_has_subdup_err.json"))

    # use v2 parse v1
    with pytest.raises(NBESFParseErr):
        v2.nbesf_parser(get_json("v1/subs_export_has_subdup_err.json"))
    # # use v2 parse v3
    # with pytest.raises(NBESFParseErr):
    #     v2.nbesf_parser(get_json("v3/subs_export_has_subdup_err.json"))

    # use v3 parse v1
    with pytest.raises(NBESFParseErr):
        v3.nbesf_parser(get_json("v1/subs_export_has_subdup_err.json"))
    # # use v3 parse v2
    # with pytest.raises(NBESFParseErr):
    #     v3.nbesf_parser(get_json("v2/subs_export_has_subdup_err.json"))
    # TODO: v3 parse v2 不会报错，但是v3 parse v1 会报错，似乎是有问题 (

    with pytest.raises(AssertionError):  # noqa: PT012
        nbesf_data = v2.nbesf_parser(get_json("v2/subs_export_has_subdup_err.json"))
        nbesf_data.version = 1
        await subscribes_import(nbesf_data)


async def test_subs_import_all_fail(app: App, init_scheduler):
    """只要文件格式有任何一个错误， 都不会进行订阅"""
    from nonebot_bison.config.subs_io.nbesf_model import v1, v2, v3
    from nonebot_bison.config.subs_io.nbesf_model.v1 import NBESFParseErr

    with pytest.raises(NBESFParseErr):
        v1.nbesf_parser(get_json("v1/subs_export_all_illegal.json"))

    with pytest.raises(NBESFParseErr):
        v2.nbesf_parser(get_json("v2/subs_export_all_illegal.json"))

    with pytest.raises(NBESFParseErr):
        v3.nbesf_parser(get_json("v3/subs_export_all_illegal.json"))
