import json
from typing import cast

from nonebug import App


async def test_cookie(app: App, init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.platform import site_manager
    from nonebot_bison.config.db_config import config
    from nonebot_bison.types import Target as T_Target
    from nonebot_bison.utils.site import CookieClientManager

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
    client_mgr = cast(CookieClientManager, site.client_mgr)

    await client_mgr.refresh_anonymous_cookie()  # 刷新匿名cookie

    cookies = await config.get_cookie(site_name=site.name)
    assert len(cookies) == 1

    await client_mgr.add_user_cookie(json.dumps({"test_cookie": "1"}))
    await client_mgr.add_user_cookie(json.dumps({"test_cookie": "2"}))

    cookies = await config.get_cookie(site_name=site.name)
    assert len(cookies) == 3

    cookies = await config.get_cookie(site_name=site.name, is_anonymous=False)
    assert len(cookies) == 2

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
    await client_mgr.add_user_cookie(json.dumps({"test_cookie": "3"}))
    cookies = await config.get_cookie(site_name=site.name, is_anonymous=False)

    await config.add_cookie_target(target2, platform_name, cookies[0].id)
    await config.add_cookie_target(target2, platform_name, cookies[2].id)

    cookies = await config.get_cookie(site_name=site.name, target=target2)
    assert len(cookies) == 3

    cookies = await config.get_cookie(site_name=site.name, target=target2, is_anonymous=False)
    assert len(cookies) == 2
