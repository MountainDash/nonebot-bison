from nonebug.app import App


async def test_add_subscrib(app: App):

    from nonebot_bison.config.db_config import config
    from nonebot_bison.types import Target

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=Target("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
