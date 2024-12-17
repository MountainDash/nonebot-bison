from nonebug import App
import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [{"refresh_bot": True}], indirect=True)
async def test_get_bots(app: App) -> None:
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Bot as BotV11
    from nonebot.adapters.onebot.v12 import Bot as BotV12

    from nonebot_bison.utils.get_bot import get_bots

    async with app.test_api() as ctx:
        botv11 = ctx.create_bot(base=BotV11, self_id="v11")
        botv12 = ctx.create_bot(base=BotV12, self_id="v12", platform="qq", impl="walle")

        driver = get_driver()
        driver._bots = {botv11.self_id: botv11, botv12.self_id: botv12}

        bot = get_bots()

        assert botv11 in bot
        assert botv12 not in bot
