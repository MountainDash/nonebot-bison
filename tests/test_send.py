import asyncio

import pytest
from nonebot.adapters.onebot.v11.bot import Bot
from nonebug import App


@pytest.mark.asyncio
async def test_send_no_queue(app: App):
    import nonebot
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.send import send_msgs

    async with app.test_api() as ctx:
        app.monkeypatch.setattr(plugin_config, "bison_use_queue", False, True)
        bot = ctx.create_bot(base=Bot)
        assert isinstance(bot, Bot)
        ctx.should_call_api(
            "send_group_msg", {"group_id": "1233", "message": "msg1"}, True
        )
        ctx.should_call_api(
            "send_group_msg", {"group_id": "1233", "message": "msg2"}, True
        )
        await send_msgs(bot, "1233", "group", ["msg1", "msg2"])


@pytest.mark.asyncio
async def test_send_queue(app: App):
    import nonebot
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.send import LAST_SEND_TIME, do_send_msgs, send_msgs

    async with app.test_api() as ctx:
        new_bot = ctx.create_bot(base=Bot)
        app.monkeypatch.setattr(nonebot, "get_bot", lambda: new_bot, True)
        app.monkeypatch.setattr(plugin_config, "bison_use_queue", True, True)
        bot = nonebot.get_bot()
        assert isinstance(bot, Bot)
        assert bot == new_bot
        ctx.should_call_api(
            "send_group_msg", {"group_id": "1233", "message": "test msg"}, True
        )
        await bot.call_api("send_group_msg", group_id="1233", message="test msg")
        await send_msgs(bot, "1233", "group", ["msg"])
        ctx.should_call_api(
            "send_group_msg", {"group_id": "1233", "message": "msg"}, True
        )
        LAST_SEND_TIME = 0
        await asyncio.sleep(2)
        await do_send_msgs()
        assert ctx.wait_list.empty()
