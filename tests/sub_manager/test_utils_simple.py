from nonebug.app import App
import pytest


@pytest.mark.usefixtures("_clear_db")
async def test_get_cookie_target_platforms_empty(app: App):
    """Test get_cookie_target_platforms with no cookie targets"""
    from nonebot_bison.sub_manager.utils import get_cookie_target_platforms

    platforms = await get_cookie_target_platforms()

    # Should return an empty set
    assert isinstance(platforms, set)
    assert len(platforms) == 0


@pytest.mark.usefixtures("_clear_db")
@pytest.mark.usefixtures("_patch_weibo_get_cookie_name")
async def test_get_cookie_target_platforms_with_data(app: App):
    """Test get_cookie_target_platforms with cookie targets"""
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.config.db_model import Cookie
    from nonebot_bison.sub_manager.utils import get_cookie_target_platforms
    from nonebot_bison.types import Target as T_Target

    # Setup test data
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
    await config.add_cookie(Cookie(content='{"cookie": "test"}', site_name="weibo.com"))
    cookies = await config.get_cookie(is_anonymous=False)
    await config.add_cookie_target(target, platform_name, cookies[0].id)

    platforms = await get_cookie_target_platforms()

    # Should return a set with platform names
    assert isinstance(platforms, set)
    assert "weibo" in platforms
    assert len(platforms) == 1


@pytest.mark.usefixtures("_clear_db")
async def test_get_platform_cookie_targets(app: App):
    """Test get_platform_cookie_targets function"""
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.config.db_model import Cookie
    from nonebot_bison.sub_manager.utils import get_platform_cookie_targets
    from nonebot_bison.types import Target as T_Target

    # Setup test data for multiple platforms
    weibo_target = T_Target("weibo_id")
    bilibili_target = T_Target("bilibili_id")

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=weibo_target,
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=bilibili_target,
        target_name="bilibili_name",
        platform_name="bilibili",
        cats=[],
        tags=[],
    )

    await config.add_cookie(Cookie(content='{"cookie": "test1"}', site_name="weibo.com"))
    await config.add_cookie(Cookie(content='{"cookie": "test2"}', site_name="bilibili.com"))

    cookies = await config.get_cookie(is_anonymous=False)
    weibo_cookie = next(c for c in cookies if c.site_name == "weibo.com")
    bilibili_cookie = next(c for c in cookies if c.site_name == "bilibili.com")

    await config.add_cookie_target(weibo_target, "weibo", weibo_cookie.id)
    await config.add_cookie_target(bilibili_target, "bilibili", bilibili_cookie.id)

    # Test filtering by platform
    weibo_targets = await get_platform_cookie_targets("weibo")
    bilibili_targets = await get_platform_cookie_targets("bilibili")

    assert len(weibo_targets) == 1
    assert len(bilibili_targets) == 1
    assert weibo_targets[0].target.platform_name == "weibo"
    assert bilibili_targets[0].target.platform_name == "bilibili"


@pytest.mark.usefixtures("_clear_db")
async def test_get_cookie_supported_platforms(app: App):
    """Test get_cookie_supported_platforms function"""
    from nonebot_bison.sub_manager.utils import get_cookie_supported_platforms

    platforms = await get_cookie_supported_platforms()

    # Should return a dictionary
    assert isinstance(platforms, dict)

    # Should include platforms that support cookies
    assert "weibo" in platforms
    assert "bilibili" in platforms
    assert "rss" in platforms

    # Values should match keys
    for key, value in platforms.items():
        assert key == value
