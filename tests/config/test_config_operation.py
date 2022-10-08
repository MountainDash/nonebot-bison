import pytest
from nonebug.app import App
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.functions import func
from sqlmodel.sql.expression import select


async def test_add_subscribe(app: App, init_scheduler):

    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.db_model import Subscribe, Target, User
    from nonebot_bison.types import Target as TTarget
    from nonebot_plugin_datastore.db import get_engine

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        user=234,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    confs = await config.list_subscribe(123, "group")
    assert len(confs) == 1
    conf: Subscribe = confs[0]
    async with AsyncSession(get_engine()) as sess:
        related_user_obj = await sess.scalar(
            select(User).where(User.id == conf.user_id)
        )
        related_target_obj = await sess.scalar(
            select(Target).where(Target.id == conf.target_id)
        )
    assert related_user_obj.uid == 123
    assert related_target_obj.target_name == "weibo_name"
    assert related_target_obj.target == "weibo_id"
    assert conf.target.target == "weibo_id"
    assert conf.categories == []

    await config.update_subscribe(
        user=123,
        user_type="group",
        target=TTarget("weibo_id"),
        platform_name="weibo",
        target_name="weibo_name2",
        cats=[1],
        tags=["tag"],
    )
    confs = await config.list_subscribe(123, "group")
    assert len(confs) == 1
    conf: Subscribe = confs[0]
    async with AsyncSession(get_engine()) as sess:
        related_user_obj = await sess.scalar(
            select(User).where(User.id == conf.user_id)
        )
        related_target_obj = await sess.scalar(
            select(Target).where(Target.id == conf.target_id)
        )
    assert related_user_obj.uid == 123
    assert related_target_obj.target_name == "weibo_name2"
    assert related_target_obj.target == "weibo_id"
    assert conf.target.target == "weibo_id"
    assert conf.categories == [1]
    assert conf.tags == ["tag"]


async def test_add_dup_sub(init_scheduler):

    from nonebot_bison.config.db_config import SubscribeDupException, config
    from nonebot_bison.types import Target as TTarget

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )

    with pytest.raises(SubscribeDupException):
        await config.add_subscribe(
            user=123,
            user_type="group",
            target=TTarget("weibo_id"),
            target_name="weibo_name",
            platform_name="weibo",
            cats=[],
            tags=[],
        )


async def test_del_subsribe(init_scheduler):
    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.db_model import Subscribe, Target, User
    from nonebot_bison.types import Target as TTarget
    from nonebot_plugin_datastore.db import get_engine

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.del_subscribe(
        user=123,
        user_type="group",
        target=TTarget("weibo_id"),
        platform_name="weibo",
    )
    async with AsyncSession(get_engine()) as sess:
        assert (await sess.scalar(select(func.count()).select_from(Subscribe))) == 0
        assert (await sess.scalar(select(func.count()).select_from(Target))) == 1

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )

    await config.add_subscribe(
        user=124,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name_new",
        platform_name="weibo",
        cats=[],
        tags=[],
    )

    await config.del_subscribe(
        user=123,
        user_type="group",
        target=TTarget("weibo_id"),
        platform_name="weibo",
    )

    async with AsyncSession(get_engine()) as sess:
        assert (await sess.scalar(select(func.count()).select_from(Subscribe))) == 1
        assert (await sess.scalar(select(func.count()).select_from(Target))) == 1
        target: Target = await sess.scalar(select(Target))
        assert target.target_name == "weibo_name_new"
