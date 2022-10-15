async def test_migration(use_legacy_config):
    from nonebot_bison.config.config_legacy import config as config_legacy
    from nonebot_bison.config.db import upgrade_db
    from nonebot_bison.config.db_config import config

    config_legacy.add_subscribe(
        user=123,
        user_type="group",
        target="weibo_id",
        target_name="weibo_name",
        target_type="weibo",
        cats=[2, 3],
        tags=[],
    )
    config_legacy.add_subscribe(
        user=123,
        user_type="group",
        target="weibo_id2",
        target_name="weibo_name2",
        target_type="weibo",
        cats=[1, 2],
        tags=["tag"],
    )
    config_legacy.add_subscribe(
        user=234,
        user_type="group",
        target="weibo_id",
        target_name="weibo_name",
        target_type="weibo",
        cats=[1],
        tags=[],
    )
    # await data_migrate()
    await upgrade_db()
    user123_config = await config.list_subscribe(123, "group")
    assert len(user123_config) == 2
    for c in user123_config:
        if c.target.target == "weibo_id":
            assert c.categories == [2, 3]
            assert c.target.target_name == "weibo_name"
            assert c.target.platform_name == "weibo"
            assert c.tags == []
        elif c.target.target == "weibo_id2":
            assert c.categories == [1, 2]
            assert c.target.target_name == "weibo_name2"
            assert c.target.platform_name == "weibo"
            assert c.tags == ["tag"]
    user234_config = await config.list_subscribe(234, "group")
    assert len(user234_config) == 1
    assert user234_config[0].categories == [1]
    assert user234_config[0].target.target == "weibo_id"
    assert user234_config[0].target.target_name == "weibo_name"
    assert user234_config[0].tags == []


async def test_migrate_dup(use_legacy_config):
    from nonebot_bison.config.config_legacy import config as config_legacy
    from nonebot_bison.config.db import upgrade_db
    from nonebot_bison.config.db_config import config

    config_legacy.add_subscribe(
        user=123,
        user_type="group",
        target="weibo_id",
        target_name="weibo_name",
        target_type="weibo",
        cats=[2, 3],
        tags=[],
    )
    config_legacy.add_subscribe(
        user=123,
        user_type="group",
        target="weibo_id",
        target_name="weibo_name",
        target_type="weibo",
        cats=[2, 3],
        tags=[],
    )
    # await data_migrate()
    await upgrade_db()
    user123_config = await config.list_subscribe(123, "group")
    assert len(user123_config) == 1
