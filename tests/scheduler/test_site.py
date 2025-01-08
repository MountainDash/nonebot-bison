from datetime import time
import typing
from unittest.mock import AsyncMock

from nonebug import App
from pytest_mock import MockerFixture

from tests.conftest import patch_refresh_bilibili_anonymous_cookie

if typing.TYPE_CHECKING:
    from nonebot_bison.utils import Site


async def get_schedule_times(site: type["Site"], time: int) -> dict[str, int]:
    from nonebot_bison.scheduler import scheduler_dict

    scheduler = scheduler_dict[site]
    res = {}
    for _ in range(time):
        schedulable = await scheduler.get_next_schedulable()
        assert schedulable
        key = f"{schedulable.platform_name}-{schedulable.target}"
        res[key] = res.get(key, 0) + 1
    return res


async def test_scheduler_without_time(init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.config.db_config import WeightConfig
    from nonebot_bison.platform.ncm import NcmSite
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "ncm-artist", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "ncm-artist", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "ncm-radio", [], [])

    await config.update_time_weight_config(T_Target("t2"), "ncm-artist", WeightConfig(default=20, time_config=[]))
    await config.update_time_weight_config(T_Target("t2"), "ncm-radio", WeightConfig(default=30, time_config=[]))

    await init_scheduler()

    static_res = await get_schedule_times(NcmSite, 6)
    assert static_res["ncm-artist-t1"] == 1
    assert static_res["ncm-artist-t2"] == 2
    assert static_res["ncm-radio-t2"] == 3

    static_res = await get_schedule_times(NcmSite, 6)
    assert static_res["ncm-artist-t1"] == 1
    assert static_res["ncm-artist-t2"] == 2
    assert static_res["ncm-radio-t2"] == 3


async def test_scheduler_batch_api(init_scheduler, mocker: MockerFixture):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.platform.bilibili import BililiveSite
    from nonebot_bison.scheduler import scheduler_dict
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.types import Target as T_Target
    from nonebot_bison.types import UserSubInfo
    from nonebot_bison.utils import DefaultClientManager

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "bilibili-live", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target2", "bilibili-live", [], [])

    mocker.patch.object(BililiveSite, "client_mgr", DefaultClientManager)

    await init_scheduler()

    batch_fetch_mock = AsyncMock()

    class FakePlatform:
        def __init__(self) -> None:
            self.do_batch_fetch_new_post = batch_fetch_mock
            self.site = BililiveSite

    fake_platform_obj = FakePlatform()
    mocker.patch.dict(
        "nonebot_bison.scheduler.scheduler.platform_manager",
        {"bilibili-live": mocker.Mock(return_value=fake_platform_obj)},
    )

    await scheduler_dict[BililiveSite].exec_fetch()

    batch_fetch_mock.assert_called_once_with(
        [
            (T_Target("t1"), [UserSubInfo(user=TargetQQGroup(group_id=123), categories=[], tags=[])]),
            (T_Target("t2"), [UserSubInfo(user=TargetQQGroup(group_id=123), categories=[], tags=[])]),
        ]
    )


async def test_scheduler_with_time(app: App, init_scheduler, mocker: MockerFixture):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config, db_config
    from nonebot_bison.config.db_config import TimeWeightConfig, WeightConfig
    from nonebot_bison.platform.ncm import NcmSite
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "ncm-artist", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "ncm-artist", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "ncm-radio", [], [])

    await config.update_time_weight_config(
        T_Target("t2"),
        "ncm-artist",
        WeightConfig(
            default=20,
            time_config=[TimeWeightConfig(start_time=time(10), end_time=time(11), weight=1000)],
        ),
    )
    await config.update_time_weight_config(T_Target("t2"), "ncm-radio", WeightConfig(default=30, time_config=[]))

    await init_scheduler()

    mocker.patch.object(db_config, "_get_time", return_value=time(1, 30))

    static_res = await get_schedule_times(NcmSite, 6)
    assert static_res["ncm-artist-t1"] == 1
    assert static_res["ncm-artist-t2"] == 2
    assert static_res["ncm-radio-t2"] == 3

    static_res = await get_schedule_times(NcmSite, 6)
    assert static_res["ncm-artist-t1"] == 1
    assert static_res["ncm-artist-t2"] == 2
    assert static_res["ncm-radio-t2"] == 3

    mocker.patch.object(db_config, "_get_time", return_value=time(10, 30))

    static_res = await get_schedule_times(NcmSite, 6)
    assert static_res["ncm-artist-t2"] == 6


async def test_scheduler_add_new(init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.platform.bilibili import BilibiliSite
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "bilibili", [], [])

    await init_scheduler()

    await config.add_subscribe(TargetQQGroup(group_id=2345), T_Target("t1"), "target1", "bilibili", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target2", "bilibili", [], [])
    stat_res = await get_schedule_times(BilibiliSite, 1)
    assert stat_res["bilibili-t2"] == 1


async def test_schedule_delete(init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.platform.bilibili import BilibiliSite
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "bilibili", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "bilibili", [], [])

    await init_scheduler()

    stat_res = await get_schedule_times(BilibiliSite, 2)
    assert stat_res["bilibili-t2"] == 1
    assert stat_res["bilibili-t1"] == 1

    await config.del_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "bilibili")
    stat_res = await get_schedule_times(BilibiliSite, 2)
    assert stat_res["bilibili-t2"] == 2


async def test_scheduler_skip_browser(mocker: MockerFixture):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.platform import NewMessage
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.scheduler import init_scheduler, scheduler_dict
    from nonebot_bison.scheduler.scheduler import Site

    mocker.patch.object(plugin_config, "bison_use_browser", False)

    class MockSite(Site):
        name = "mock_site"
        schedule_type = "interval"
        schedule_setting: typing.ClassVar[dict] = {"seconds": 100}
        require_browser = True

    class MockPlatform(NewMessage):
        platform_name = "mock_platform"
        name = "Mock Platform"
        enabled = True
        is_common = True
        enable_tag = True
        has_target = True
        site = MockSite

    mocker.patch.dict(platform_manager, {"mock_platform": MockPlatform})
    patch_refresh_bilibili_anonymous_cookie(mocker)

    await init_scheduler()

    assert MockSite not in scheduler_dict.keys()


async def test_scheduler_no_skip_not_require_browser(mocker: MockerFixture):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.platform import NewMessage
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.scheduler import init_scheduler, scheduler_dict
    from nonebot_bison.scheduler.scheduler import Site

    mocker.patch.object(plugin_config, "bison_use_browser", False)

    class MockSite(Site):
        name = "mock_site"
        schedule_type = "interval"
        schedule_setting: typing.ClassVar[dict] = {"seconds": 100}

    class MockPlatform(NewMessage):
        platform_name = "mock_platform"
        name = "Mock Platform"
        enabled = True
        is_common = True
        enable_tag = True
        has_target = True
        site = MockSite

    mocker.patch.dict(platform_manager, {"mock_platform": MockPlatform})
    patch_refresh_bilibili_anonymous_cookie(mocker)

    await init_scheduler()

    assert MockSite in scheduler_dict.keys()
