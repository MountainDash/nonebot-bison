import pytest
from nonebug import App

from .utils import AppReq


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [{"refresh_bot": True}], indirect=True)
async def test_get_bots(app: App) -> None:
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Bot as BotV11
    from nonebot.adapters.onebot.v12 import Bot as BotV12

    from nonebot_bison.utils.get_bot import get_bots

    async with app.test_api() as ctx:
        botv11 = ctx.create_bot(base=BotV11, self_id="v11")
        botv12 = ctx.create_bot(base=BotV12, self_id="v12", platform="qq")

        driver = get_driver()
        driver._bots = {botv11.self_id: botv11, botv12.self_id: botv12}

        bot = get_bots()

        assert botv11 in bot
        assert botv12 not in bot


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [{"refresh_bot": True}], indirect=True)
async def test_refresh_bots(app: App) -> None:
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Bot as BotV11
    from nonebot.adapters.onebot.v12 import Bot as BotV12

    from nonebot_bison.types import User
    from nonebot_bison.utils.get_bot import get_bot, get_groups, refresh_bots

    async with app.test_api() as ctx:
        botv11 = ctx.create_bot(base=BotV11, self_id="v11")
        botv12 = ctx.create_bot(base=BotV12, self_id="v12", platform="qq")

        driver = get_driver()
        driver._bots = {botv11.self_id: botv11, botv12.self_id: botv12}

        ctx.should_call_api("get_group_list", {}, [{"group_id": 1}])
        ctx.should_call_api("get_friend_list", {}, [{"user_id": 2}])

        assert get_bot(User(1, "group")) is None
        assert get_bot(User(2, "private")) is None

        await refresh_bots()

        assert get_bot(User(1, "group")) == botv11
        assert get_bot(User(2, "private")) == botv11

        # 测试获取群列表
        ctx.should_call_api("get_group_list", {}, [{"group_id": 3}])

        groups = await get_groups()

        assert groups == [{"group_id": 3}]


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [{"refresh_bot": True}], indirect=True)
async def test_get_bot_two_bots(app: App) -> None:
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Bot as BotV11
    from nonebot.adapters.onebot.v12 import Bot as BotV12

    from nonebot_bison.types import User
    from nonebot_bison.utils.get_bot import get_bot, get_groups, refresh_bots

    async with app.test_api() as ctx:
        bot1 = ctx.create_bot(base=BotV11, self_id="1")
        bot2 = ctx.create_bot(base=BotV11, self_id="2")
        botv12 = ctx.create_bot(base=BotV12, self_id="v12", platform="qq")

        driver = get_driver()
        driver._bots = {bot1.self_id: bot1, bot2.self_id: bot2, botv12.self_id: botv12}

        ctx.should_call_api("get_group_list", {}, [{"group_id": 1}, {"group_id": 2}])
        ctx.should_call_api("get_friend_list", {}, [{"user_id": 1}, {"user_id": 2}])
        ctx.should_call_api("get_group_list", {}, [{"group_id": 2}, {"group_id": 3}])
        ctx.should_call_api("get_friend_list", {}, [{"user_id": 2}, {"user_id": 3}])

        await refresh_bots()

        assert get_bot(User(0, "group")) is None
        assert get_bot(User(1, "group")) == bot1
        assert get_bot(User(2, "group")) in (bot1, bot2)
        assert get_bot(User(3, "group")) == bot2
        assert get_bot(User(0, "private")) is None
        assert get_bot(User(1, "private")) == bot1
        assert get_bot(User(2, "private")) in (bot1, bot2)
        assert get_bot(User(3, "private")) == bot2

        ctx.should_call_api("get_group_list", {}, [{"group_id": 1}, {"group_id": 2}])
        ctx.should_call_api("get_group_list", {}, [{"group_id": 2}, {"group_id": 3}])

        groups = await get_groups()

        assert groups == [{"group_id": 1}, {"group_id": 2}, {"group_id": 3}]
