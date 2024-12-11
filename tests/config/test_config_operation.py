from nonebug.app import App
import pytest


async def test_add_subscribe(app: App, init_scheduler):
    from nonebot_plugin_datastore.db import get_engine
    from nonebot_plugin_saa import TargetQQGroup
    from sqlalchemy.ext.asyncio.session import AsyncSession
    from sqlalchemy.sql.expression import select

    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.db_model import Subscribe, Target, User
    from nonebot_bison.types import Target as TTarget

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        TargetQQGroup(group_id=234),
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    confs = await config.list_subscribe(TargetQQGroup(group_id=123))
    assert len(confs) == 1
    conf: Subscribe = confs[0]
    async with AsyncSession(get_engine()) as sess:
        related_user_obj = await sess.scalar(select(User).where(User.id == conf.user_id))
        related_target_obj = await sess.scalar(select(Target).where(Target.id == conf.target_id))
    assert related_user_obj
    assert related_target_obj
    assert related_user_obj.user_target["group_id"] == 123
    assert related_target_obj.target_name == "weibo_name"
    assert related_target_obj.target == "weibo_id"
    assert conf.target.target == "weibo_id"
    assert conf.categories == []

    await config.update_subscribe(
        TargetQQGroup(group_id=123),
        target=TTarget("weibo_id"),
        platform_name="weibo",
        target_name="weibo_name2",
        cats=[1],
        tags=["tag"],
    )
    confs = await config.list_subscribe(TargetQQGroup(group_id=123))
    assert len(confs) == 1
    conf2: Subscribe = confs[0]
    async with AsyncSession(get_engine()) as sess:
        related_user_obj = await sess.scalar(select(User).where(User.id == conf2.user_id))
        related_target_obj = await sess.scalar(select(Target).where(Target.id == conf2.target_id))
    assert related_user_obj
    assert related_target_obj
    assert related_user_obj.user_target["group_id"] == 123
    assert related_target_obj.target_name == "weibo_name2"
    assert related_target_obj.target == "weibo_id"
    assert conf2.target.target == "weibo_id"
    assert conf2.categories == [1]
    assert conf2.tags == ["tag"]


async def test_add_dup_sub(init_scheduler):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.config.db_config import SubscribeDupException, config
    from nonebot_bison.types import Target as TTarget

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )

    with pytest.raises(SubscribeDupException):
        await config.add_subscribe(
            TargetQQGroup(group_id=123),
            target=TTarget("weibo_id"),
            target_name="weibo_name",
            platform_name="weibo",
            cats=[],
            tags=[],
        )


async def test_del_subsribe(init_scheduler):
    from nonebot_plugin_datastore.db import get_engine
    from nonebot_plugin_saa import TargetQQGroup
    from sqlalchemy.ext.asyncio.session import AsyncSession
    from sqlalchemy.sql.expression import select
    from sqlalchemy.sql.functions import func

    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.db_model import Subscribe, Target
    from nonebot_bison.types import Target as TTarget

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.del_subscribe(
        TargetQQGroup(group_id=123),
        target=TTarget("weibo_id"),
        platform_name="weibo",
    )
    async with AsyncSession(get_engine()) as sess:
        assert (await sess.scalar(select(func.count()).select_from(Subscribe))) == 0
        assert (await sess.scalar(select(func.count()).select_from(Target))) == 1

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )

    await config.add_subscribe(
        TargetQQGroup(group_id=124),
        target=TTarget("weibo_id"),
        target_name="weibo_name_new",
        platform_name="weibo",
        cats=[],
        tags=[],
    )

    await config.del_subscribe(
        TargetQQGroup(group_id=123),
        target=TTarget("weibo_id"),
        platform_name="weibo",
    )

    async with AsyncSession(get_engine()) as sess:
        assert (await sess.scalar(select(func.count()).select_from(Subscribe))) == 1
        assert (await sess.scalar(select(func.count()).select_from(Target))) == 1
        target = await sess.scalar(select(Target))
        assert target
        assert target.target_name == "weibo_name_new"
