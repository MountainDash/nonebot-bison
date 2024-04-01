import typing
from datetime import time
from unittest.mock import AsyncMock

from nonebug import App
from httpx import AsyncClient
from pytest_mock import MockerFixture

if typing.TYPE_CHECKING:
    from nonebot_bison.utils.scheduler_config import SchedulerConfig


async def get_schedule_times(scheduler_config: type["SchedulerConfig"], time: int) -> dict[str, int]:
    from nonebot_bison.scheduler import scheduler_dict

    scheduler = scheduler_dict[scheduler_config]
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
    from nonebot_bison.types import Target as T_Target
    from nonebot_bison.config.db_config import WeightConfig
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.platform.bilibili import BilibiliSchedConf

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "bilibili", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "bilibili", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "bilibili-bangumi", [], [])

    await config.update_time_weight_config(T_Target("t2"), "bilibili", WeightConfig(default=20, time_config=[]))
    await config.update_time_weight_config(T_Target("t2"), "bilibili-bangumi", WeightConfig(default=30, time_config=[]))

    await init_scheduler()

    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t1"] == 1
    assert static_res["bilibili-t2"] == 2
    assert static_res["bilibili-bangumi-t2"] == 3

    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t1"] == 1
    assert static_res["bilibili-t2"] == 2
    assert static_res["bilibili-bangumi-t2"] == 3


async def test_scheduler_batch_api(init_scheduler, mocker: MockerFixture):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.types import UserSubInfo
    from nonebot_bison.scheduler import scheduler_dict
    from nonebot_bison.types import Target as T_Target
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.platform.bilibili import BililiveSchedConf

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "bilibili-live", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target2", "bilibili-live", [], [])

    mocker.patch.object(BililiveSchedConf, "get_client", return_value=AsyncClient())

    await init_scheduler()

    batch_fetch_mock = AsyncMock()

    class FakePlatform:
        def __init__(self) -> None:
            self.do_batch_fetch_new_post = batch_fetch_mock

    fake_platform_obj = FakePlatform()
    mocker.patch.dict(
        "nonebot_bison.scheduler.scheduler.platform_manager",
        {"bilibili-live": mocker.Mock(return_value=fake_platform_obj)},
    )

    await scheduler_dict[BililiveSchedConf].exec_fetch()

    batch_fetch_mock.assert_called_once_with(
        [
            (T_Target("t1"), [UserSubInfo(user=TargetQQGroup(group_id=123), categories=[], tags=[])]),
            (T_Target("t2"), [UserSubInfo(user=TargetQQGroup(group_id=123), categories=[], tags=[])]),
        ]
    )


async def test_scheduler_with_time(app: App, init_scheduler, mocker: MockerFixture):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config, db_config
    from nonebot_bison.types import Target as T_Target
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.platform.bilibili import BilibiliSchedConf
    from nonebot_bison.config.db_config import WeightConfig, TimeWeightConfig

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "bilibili", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "bilibili", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "bilibili-bangumi", [], [])

    await config.update_time_weight_config(
        T_Target("t2"),
        "bilibili",
        WeightConfig(
            default=20,
            time_config=[TimeWeightConfig(start_time=time(10), end_time=time(11), weight=1000)],
        ),
    )
    await config.update_time_weight_config(T_Target("t2"), "bilibili-bangumi", WeightConfig(default=30, time_config=[]))

    await init_scheduler()

    mocker.patch.object(db_config, "_get_time", return_value=time(1, 30))

    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t1"] == 1
    assert static_res["bilibili-t2"] == 2
    assert static_res["bilibili-bangumi-t2"] == 3

    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t1"] == 1
    assert static_res["bilibili-t2"] == 2
    assert static_res["bilibili-bangumi-t2"] == 3

    mocker.patch.object(db_config, "_get_time", return_value=time(10, 30))

    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t2"] == 6


async def test_scheduler_add_new(init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.types import Target as T_Target
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.platform.bilibili import BilibiliSchedConf

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "bilibili", [], [])

    await init_scheduler()

    await config.add_subscribe(TargetQQGroup(group_id=2345), T_Target("t1"), "target1", "bilibili", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target2", "bilibili", [], [])
    stat_res = await get_schedule_times(BilibiliSchedConf, 1)
    assert stat_res["bilibili-t2"] == 1


async def test_schedule_delete(init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.types import Target as T_Target
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.platform.bilibili import BilibiliSchedConf

    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "target1", "bilibili", [], [])
    await config.add_subscribe(TargetQQGroup(group_id=123), T_Target("t2"), "target1", "bilibili", [], [])

    await init_scheduler()

    stat_res = await get_schedule_times(BilibiliSchedConf, 2)
    assert stat_res["bilibili-t2"] == 1
    assert stat_res["bilibili-t1"] == 1

    await config.del_subscribe(TargetQQGroup(group_id=123), T_Target("t1"), "bilibili")
    stat_res = await get_schedule_times(BilibiliSchedConf, 2)
    assert stat_res["bilibili-t2"] == 2
