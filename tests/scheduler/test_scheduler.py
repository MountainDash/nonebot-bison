import typing
from datetime import time
from typing import Type

from nonebug import App

if typing.TYPE_CHECKING:
    from nonebot_bison.utils.scheduler_config import SchedulerConfig


async def get_schedule_times(
    scheduler_config: Type["SchedulerConfig"], time: int
) -> dict[str, int]:
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
    from nonebot_bison.config import config
    from nonebot_bison.config.db_config import WeightConfig
    from nonebot_bison.platform.bilibili import BilibiliSchedConf
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(
        123, "group", T_Target("t1"), "target1", "bilibili", [], []
    )
    await config.add_subscribe(
        123, "group", T_Target("t2"), "target1", "bilibili", [], []
    )
    await config.add_subscribe(
        123, "group", T_Target("t2"), "target1", "bilibili-live", [], []
    )

    await config.update_time_weight_config(
        T_Target("t2"), "bilibili", WeightConfig(default=20, time_config=[])
    )
    await config.update_time_weight_config(
        T_Target("t2"), "bilibili-live", WeightConfig(default=30, time_config=[])
    )

    await init_scheduler()

    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t1"] == 1
    assert static_res["bilibili-t2"] == 2
    assert static_res["bilibili-live-t2"] == 3

    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t1"] == 1
    assert static_res["bilibili-t2"] == 2
    assert static_res["bilibili-live-t2"] == 3


async def test_scheduler_with_time(app: App, init_scheduler):
    from nonebot_bison.config import config, db_config
    from nonebot_bison.config.db_config import TimeWeightConfig, WeightConfig
    from nonebot_bison.platform.bilibili import BilibiliSchedConf
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(
        123, "group", T_Target("t1"), "target1", "bilibili", [], []
    )
    await config.add_subscribe(
        123, "group", T_Target("t2"), "target1", "bilibili", [], []
    )
    await config.add_subscribe(
        123, "group", T_Target("t2"), "target1", "bilibili-live", [], []
    )

    await config.update_time_weight_config(
        T_Target("t2"),
        "bilibili",
        WeightConfig(
            default=20,
            time_config=[
                TimeWeightConfig(start_time=time(10), end_time=time(11), weight=1000)
            ],
        ),
    )
    await config.update_time_weight_config(
        T_Target("t2"), "bilibili-live", WeightConfig(default=30, time_config=[])
    )

    await init_scheduler()

    app.monkeypatch.setattr(db_config, "_get_time", lambda: time(1, 30))
    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t1"] == 1
    assert static_res["bilibili-t2"] == 2
    assert static_res["bilibili-live-t2"] == 3

    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t1"] == 1
    assert static_res["bilibili-t2"] == 2
    assert static_res["bilibili-live-t2"] == 3

    app.monkeypatch.setattr(db_config, "_get_time", lambda: time(10, 30))

    static_res = await get_schedule_times(BilibiliSchedConf, 6)
    assert static_res["bilibili-t2"] == 6


async def test_scheduler_add_new(init_scheduler):
    from nonebot_bison.config import config
    from nonebot_bison.platform.bilibili import BilibiliSchedConf
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(
        123, "group", T_Target("t1"), "target1", "bilibili", [], []
    )

    await init_scheduler()

    await config.add_subscribe(
        2345, "group", T_Target("t1"), "target1", "bilibili", [], []
    )
    await config.add_subscribe(
        123, "group", T_Target("t2"), "target2", "bilibili", [], []
    )
    stat_res = await get_schedule_times(BilibiliSchedConf, 1)
    assert stat_res["bilibili-t2"] == 1


async def test_schedule_delete(init_scheduler):
    from nonebot_bison.config import config
    from nonebot_bison.platform.bilibili import BilibiliSchedConf
    from nonebot_bison.scheduler.manager import init_scheduler
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(
        123, "group", T_Target("t1"), "target1", "bilibili", [], []
    )
    await config.add_subscribe(
        123, "group", T_Target("t2"), "target1", "bilibili", [], []
    )

    await init_scheduler()

    stat_res = await get_schedule_times(BilibiliSchedConf, 2)
    assert stat_res["bilibili-t2"] == 1
    assert stat_res["bilibili-t1"] == 1

    await config.del_subscribe(123, "group", T_Target("t1"), "bilibili")
    stat_res = await get_schedule_times(BilibiliSchedConf, 2)
    assert stat_res["bilibili-t2"] == 2
