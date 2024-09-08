import datetime

from nonebug import App


async def test_get_platform_target(app: App, init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config.db_config import config
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=T_Target("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    # await config.add_cookie(TargetQQGroup(group_id=123), "weibo", "cookie")
    # cookies = await config.get_cookie_by_user(TargetQQGroup(group_id=123))
    #
    # res = await config.get_platform_target("weibo")
    # assert len(res) == 2
    # await config.del_subscribe(TargetQQGroup(group_id=123), T_Target("weibo_id1"), "weibo")
    # res = await config.get_platform_target("weibo")
    # assert len(res) == 2
    # await config.del_subscribe(TargetQQGroup(group_id=123), T_Target("weibo_id"), "weibo")
    # res = await config.get_platform_target("weibo")
    # assert len(res) == 1
    #
    # async with AsyncSession(get_engine()) as sess:
    #     res = await sess.scalars(select(Target).where(Target.platform_name == "weibo"))
    #     assert len(res.all()) == 2
    # await config.get_cookie_by_user(TargetQQGroup(group_id=123))


async def test_cookie_by_user(app: App, init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config.db_config import config
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=T_Target("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )

    await config.add_cookie_with_content(TargetQQGroup(group_id=123), "weibo", "cookie")

    cookies = await config.get_cookie(TargetQQGroup(group_id=123))
    cookie = cookies[0]
    assert len(cookies) == 1
    assert cookie.content == "cookie"
    assert cookie.platform_name == "weibo"
    cookie.last_usage = 0
    assert cookie.status == ""
    assert cookie.tags == {}
    cookie.content = "cookie1"
    cookie.last_usage = datetime.datetime(2024, 8, 22, 0, 0, 0)
    cookie.status = "status1"
    cookie.tags = {"tag1": "value1"}
    await config.update_cookie(cookie)
    cookies = await config.get_cookie(TargetQQGroup(group_id=123))

    assert len(cookies) == 1
    assert cookies[0].content == cookie.content
    assert cookies[0].last_usage == cookie.last_usage
    assert cookies[0].status == cookie.status
    assert cookies[0].tags == cookie.tags

    await config.delete_cookie_by_id(cookies[0].id)
    cookies = await config.get_cookie(TargetQQGroup(group_id=123))
    assert len(cookies) == 0


async def test_cookie_target_by_target(app: App, init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config.db_config import config
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=T_Target("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )

    id = await config.add_cookie_with_content(TargetQQGroup(group_id=123), "weibo", "cookie")

    await config.add_cookie_target(T_Target("weibo_id"), "weibo", id)

    cookies = await config.get_cookie_by_target(T_Target("weibo_id"), "weibo")
    assert len(cookies) == 1
    assert cookies[0].content == "cookie"
    assert cookies[0].platform_name == "weibo"

    await config.delete_cookie_target(T_Target("weibo_id"), "weibo", id)
    cookies = await config.get_cookie_by_target(T_Target("weibo_id"), "weibo")
    assert len(cookies) == 0
