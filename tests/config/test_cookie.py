from datetime import datetime
import json
from typing import cast

from nonebug import App
import pytest


@pytest.mark.usefixtures("_patch_weibo_get_cookie_name")
async def test_cookie(app: App, init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.utils import DuplicateCookieTargetException
    from nonebot_bison.scheduler import scheduler_dict
    from nonebot_bison.types import Target as T_Target
    from nonebot_bison.utils.site import CookieClientManager, site_manager

    target = T_Target("weibo_id")
    platform_name = "weibo"
    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=target,
        target_name="weibo_name",
        platform_name=platform_name,
        cats=[],
        tags=[],
    )
    site = site_manager["weibo.com"]
    client_mgr = cast(CookieClientManager, scheduler_dict[site].client_mgr)

    # 刷新匿名cookie
    await client_mgr.refresh_client()

    cookies = await config.get_cookie(site_name=site.name)
    assert len(cookies) == 1
    # 添加实名cookie
    await client_mgr.add_identified_cookie(json.dumps({"test_cookie": "1"}))
    await client_mgr.add_identified_cookie(json.dumps({"test_cookie": "2"}))

    cookies = await config.get_cookie(site_name=site.name)
    assert len(cookies) == 3

    cookies = await config.get_cookie(site_name=site.name, is_anonymous=False)
    assert len(cookies) == 2

    # 单个target，多个cookie
    await config.add_cookie_target(target, platform_name, cookies[0].id)
    await config.add_cookie_target(target, platform_name, cookies[1].id)

    cookies = await config.get_cookie(site_name=site.name, target=target)
    assert len(cookies) == 3

    cookies = await config.get_cookie(site_name=site.name, target=target, is_anonymous=False)
    assert len(cookies) == 2

    cookies = await config.get_cookie(site_name=site.name, target=target, is_universal=False)
    assert len(cookies) == 2

    # 测试不同的target
    target2 = T_Target("weibo_id2")
    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=target2,
        target_name="weibo_name2",
        platform_name=platform_name,
        cats=[],
        tags=[],
    )

    await client_mgr.add_identified_cookie(json.dumps({"test_cookie": "3"}))
    cookies = await config.get_cookie(site_name=site.name, is_anonymous=False)

    # 多个target，多个cookie
    await config.add_cookie_target(target2, platform_name, cookies[0].id)
    await config.add_cookie_target(target2, platform_name, cookies[2].id)

    cookies = await config.get_cookie(site_name=site.name, target=target2)
    assert len(cookies) == 3

    # 重复关联 target
    with pytest.raises(DuplicateCookieTargetException) as e:
        await config.add_cookie_target(target2, platform_name, cookies[2].id)
    assert isinstance(e.value, DuplicateCookieTargetException)

    cookies = await config.get_cookie(site_name=site.name, target=target2, is_anonymous=False)
    assert len(cookies) == 2

    # 有关联的cookie不能删除
    with pytest.raises(Exception, match="cookie") as e:
        await config.delete_cookie_by_id(cookies[1].id)
    cookies = await config.get_cookie(site_name=site.name, target=target2, is_anonymous=False)
    assert len(cookies) == 2

    await config.delete_cookie_target(target2, platform_name, cookies[1].id)
    await config.delete_cookie_by_id(cookies[1].id)
    cookies = await config.get_cookie(site_name=site.name, target=target2, is_anonymous=False)
    assert len(cookies) == 1

    cookie = cookies[0]
    cookie_id = cookie.id
    cookie.last_usage = datetime(2024, 9, 13)
    cookie.status = "test"
    await config.update_cookie(cookie)
    cookies = await config.get_cookie(site_name=site.name, target=target2, is_anonymous=False)
    assert len(cookies) == 1
    assert cookies[0].id == cookie_id
    assert cookies[0].last_usage == datetime(2024, 9, 13)
    assert cookies[0].status == "test"

    # 不存在的 cookie_id
    cookie.id = 114514
    with pytest.raises(ValueError, match="cookie") as e:
        await config.update_cookie(cookie)

    # 获取所有关联对象
    cookie_targets = await config.get_cookie_target()
    assert len(cookie_targets) == 3

    # 删除关联对象
    await config.delete_cookie_target_by_id(cookie_targets[0].id)

    cookie_targets = await config.get_cookie_target()
    assert len(cookie_targets) == 2


@pytest.mark.parametrize(
    argnames=("cookie", "cookie_len"),
    argvalues=[
        (
            (
                "buvid3=7DBD8997-0677-BFC6-F33E-39621C7F12BD83823infoc; b_nut=1730004183; _uuid=110C3D7AA-5A93-2FFA"
                "-39102-002E9D916218D93681infoc; CURRENT_FNVAL=4048; buvid_fp=b005f375d5a10c359a1e3000d2ce9ff3; buv"
                "id4=2EC6FDB3-5793-4CB2-14CD-1500004C816694458-024121214-3%2BpNY9k7fQ%2B5btK5slbeYy032KrlM3%2FKYx74"
                "vbwAtQHooBkd4NQz4D93uaqjIR1s; rpdid=0zb000LZi7|dqQ6QJZH|2oO|3w1TlKiS; fingerprint=b0000075d5a10c35"
                "9a1e3bb000ce9ff3"
            ),
            8,
        ),
        ("buvid3=7DBD8997-0677-BFC6-F33E-39621C7F12BD83823infoc", 1),
        (r'{"aaa":"bbb"}', 1),
        ("{}", 0),
    ],
)
@pytest.mark.usefixtures("_patch_weibo_get_cookie_name")
def test_parse_cookie_success(cookie: str, cookie_len: int):
    from nonebot_bison.utils.site import parse_cookie

    res = parse_cookie(cookie)
    assert isinstance(res, dict)
    assert len(res) == cookie_len


@pytest.mark.parametrize(
    argnames="cookie",
    argvalues=[
        "",
        "{aa}",
        "7DBD8997-0677-BFC6-F33E-39621C7F12BD83823infoc",
        "7DBD8997-0677-BFC6-F33E-39621C7F12BD83823infoc;",
    ],
)
@pytest.mark.usefixtures("_patch_weibo_get_cookie_name")
def test_parse_cookie_failed(cookie: str):
    from nonebot_bison.utils.site import parse_cookie

    res = parse_cookie(cookie)
    assert isinstance(res, dict)
    assert len(res) == 0
