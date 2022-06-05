from datetime import time

from nonebug import App


async def test_create_config(app: App, init_scheduler):
    from nonebot_bison.config.db_config import TimeWeightConfig, WeightConfig, config
    from nonebot_bison.config.db_model import Subscribe, Target, User
    from nonebot_bison.types import Target as T_Target
    from nonebot_plugin_datastore.db import get_engine

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=T_Target("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        user=123,
        user_type="group",
        target=T_Target("weibo_id1"),
        target_name="weibo_name1",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.update_time_weight_config(
        target=T_Target("weibo_id"),
        platform_name="weibo",
        conf=WeightConfig(
            default=10,
            time_config=[
                TimeWeightConfig(start_time=time(1, 0), end_time=time(2, 0), weight=20)
            ],
        ),
    )

    test_config = await config.get_time_weight_config(
        target=T_Target("weibo_id"), platform_name="weibo"
    )
    assert test_config.default == 10
    assert test_config.time_config == [
        TimeWeightConfig(start_time=time(1, 0), end_time=time(2, 0), weight=20)
    ]
    test_config1 = await config.get_time_weight_config(
        target=T_Target("weibo_id1"), platform_name="weibo"
    )
    assert test_config1.default == 10
    assert test_config1.time_config == []


async def test_get_current_weight(app: App, init_scheduler):
    from datetime import time

    from nonebot_bison.config import db_config
    from nonebot_bison.config.db_config import TimeWeightConfig, WeightConfig, config
    from nonebot_bison.config.db_model import Subscribe, Target, User
    from nonebot_bison.types import Target as T_Target
    from nonebot_plugin_datastore.db import get_engine

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=T_Target("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        user=123,
        user_type="group",
        target=T_Target("weibo_id1"),
        target_name="weibo_name1",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        user=123,
        user_type="group",
        target=T_Target("weibo_id1"),
        target_name="weibo_name2",
        platform_name="bilibili",
        cats=[],
        tags=[],
    )
    await config.update_time_weight_config(
        target=T_Target("weibo_id"),
        platform_name="weibo",
        conf=WeightConfig(
            default=10,
            time_config=[
                TimeWeightConfig(start_time=time(1, 0), end_time=time(2, 0), weight=20),
                TimeWeightConfig(start_time=time(4, 0), end_time=time(5, 0), weight=30),
            ],
        ),
    )
    app.monkeypatch.setattr(db_config, "_get_time", lambda: time(1, 30))
    weight = await config.get_current_weight_val(["weibo", "bilibili"])
    assert len(weight) == 3
    assert weight["weibo-weibo_id"] == 20
    assert weight["weibo-weibo_id1"] == 10
    assert weight["bilibili-weibo_id1"] == 10
    app.monkeypatch.setattr(db_config, "_get_time", lambda: time(4, 0))
    weight = await config.get_current_weight_val(["weibo", "bilibili"])
    assert len(weight) == 3
    assert weight["weibo-weibo_id"] == 30
    assert weight["weibo-weibo_id1"] == 10
    assert weight["bilibili-weibo_id1"] == 10
    app.monkeypatch.setattr(db_config, "_get_time", lambda: time(5, 0))
    weight = await config.get_current_weight_val(["weibo", "bilibili"])
    assert len(weight) == 3
    assert weight["weibo-weibo_id"] == 10
    assert weight["weibo-weibo_id1"] == 10
    assert weight["bilibili-weibo_id1"] == 10


async def test_get_platform_target(app: App, init_scheduler):
    from nonebot_bison.config import db_config
    from nonebot_bison.config.db_config import TimeWeightConfig, WeightConfig, config
    from nonebot_bison.config.db_model import Subscribe, Target, User
    from nonebot_bison.types import Target as T_Target
    from nonebot_plugin_datastore.db import get_engine
    from sqlalchemy.ext.asyncio.session import AsyncSession
    from sqlalchemy.sql.expression import select

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=T_Target("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        user=123,
        user_type="group",
        target=T_Target("weibo_id1"),
        target_name="weibo_name1",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        user=245,
        user_type="group",
        target=T_Target("weibo_id1"),
        target_name="weibo_name1",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    res = await config.get_platform_target("weibo")
    assert len(res) == 2
    await config.del_subscribe(123, "group", T_Target("weibo_id1"), "weibo")
    res = await config.get_platform_target("weibo")
    assert len(res) == 2
    await config.del_subscribe(123, "group", T_Target("weibo_id"), "weibo")
    res = await config.get_platform_target("weibo")
    assert len(res) == 1

    async with AsyncSession(get_engine()) as sess:
        res = await sess.scalars(select(Target).where(Target.platform_name == "weibo"))
        assert len(res.all()) == 2


async def test_get_platform_target_subscribers(app: App, init_scheduler):
    from nonebot_bison.config import db_config
    from nonebot_bison.config.db_config import TimeWeightConfig, WeightConfig, config
    from nonebot_bison.config.db_model import Subscribe, Target, User
    from nonebot_bison.types import Target as T_Target
    from nonebot_bison.types import User as T_User
    from nonebot_bison.types import UserSubInfo
    from nonebot_plugin_datastore.db import get_engine
    from sqlalchemy.ext.asyncio.session import AsyncSession
    from sqlalchemy.sql.expression import select

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=T_Target("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[1],
        tags=["tag1"],
    )
    await config.add_subscribe(
        user=123,
        user_type="group",
        target=T_Target("weibo_id1"),
        target_name="weibo_name1",
        platform_name="weibo",
        cats=[2],
        tags=["tag2"],
    )
    await config.add_subscribe(
        user=245,
        user_type="group",
        target=T_Target("weibo_id1"),
        target_name="weibo_name1",
        platform_name="weibo",
        cats=[3],
        tags=["tag3"],
    )

    res = await config.get_platform_target_subscribers("weibo", T_Target("weibo_id"))
    assert len(res) == 1
    assert res[0] == UserSubInfo(T_User(123, "group"), [1], ["tag1"])

    res = await config.get_platform_target_subscribers("weibo", T_Target("weibo_id1"))
    assert len(res) == 2
    assert UserSubInfo(T_User(123, "group"), [2], ["tag2"]) in res
    assert UserSubInfo(T_User(245, "group"), [3], ["tag3"]) in res
