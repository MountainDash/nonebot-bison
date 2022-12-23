import pytest
from flaky import flaky
from nonebot.adapters.onebot.v11.message import Message
from nonebug import App


@pytest.mark.asyncio
async def test_send_no_queue(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.send import send_msgs

    async with app.test_api() as ctx:
        app.monkeypatch.setattr(plugin_config, "bison_use_queue", False, True)
        bot = ctx.create_bot(base=Bot)
        assert isinstance(bot, Bot)
        ctx.should_call_api(
            "send_group_msg", {"group_id": "1233", "message": Message("msg1")}, True
        )
        ctx.should_call_api(
            "send_group_msg", {"group_id": "1233", "message": Message("msg2")}, True
        )
        ctx.should_call_api(
            "send_private_msg", {"user_id": "666", "message": Message("priv")}, True
        )
        await send_msgs(bot, "1233", "group", [Message("msg1"), Message("msg2")])
        await send_msgs(bot, "666", "private", [Message("priv")])
        assert ctx.wait_list.empty()


@flaky
@pytest.mark.asyncio
async def test_send_queue(app: App):
    import nonebot
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message, MessageSegment
    from nonebot_bison import send
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.send import do_send_msgs, send_msgs

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
        await send_msgs(bot, "1233", "group", [Message("msg")])
        ctx.should_call_api(
            "send_group_msg",
            {"group_id": "1233", "message": [MessageSegment.text("msg")]},
            True,
        )
        await do_send_msgs()
        assert not ctx.wait_list.empty()
        app.monkeypatch.setattr(send, "LAST_SEND_TIME", 0, True)
        await do_send_msgs()
        assert ctx.wait_list.empty()


def gen_node(id, name, content: Message):
    return {"type": "node", "data": {"name": name, "uin": id, "content": content}}


def _merge_messge(nodes):
    return nodes


@pytest.mark.asyncio
async def test_send_merge_no_queue(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message, MessageSegment
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.send import send_msgs

    plugin_config.bison_use_pic_merge = 1
    plugin_config.bison_use_queue = False

    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=Bot, self_id="8888")
        assert isinstance(bot, Bot)
        message = [
            Message(MessageSegment.text("test msg")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
        ]
        ctx.should_call_api(
            "send_group_msg",
            {"group_id": 633, "message": Message(MessageSegment.text("test msg"))},
            None,
        )
        ctx.should_call_api(
            "send_group_msg",
            {"group_id": 633, "message": message[1]},
            None,
        )
        await send_msgs(bot, 633, "group", message)

        message = [
            Message(MessageSegment.text("test msg")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
        ]
        ctx.should_call_api(
            "send_group_msg",
            {"group_id": 633, "message": Message(MessageSegment.text("test msg"))},
            None,
        )
        ctx.should_call_api(
            "get_group_member_info",
            {"group_id": 633, "user_id": 8888, "no_cache": True},
            {"user_id": 8888, "card": "admin", "nickname": "adminuser"},
        )
        merged_message = _merge_messge(
            [gen_node(8888, "admin", message[1]), gen_node(8888, "admin", message[2])]
        )
        ctx.should_call_api(
            "send_group_forward_msg",
            {"group_id": 633, "messages": merged_message},
            None,
        )
        await send_msgs(bot, 633, "group", message)

        message = [
            Message(MessageSegment.text("test msg")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
        ]
        ctx.should_call_api(
            "send_group_msg",
            {"group_id": 633, "message": Message(MessageSegment.text("test msg"))},
            None,
        )
        ctx.should_call_api(
            "get_group_member_info",
            {"group_id": 633, "user_id": 8888, "no_cache": True},
            {"user_id": 8888, "card": None, "nickname": "adminuser"},
        )
        merged_message = _merge_messge(
            [
                gen_node(8888, "adminuser", message[1]),
                gen_node(8888, "adminuser", message[2]),
                gen_node(8888, "adminuser", message[3]),
            ]
        )
        ctx.should_call_api(
            "send_group_forward_msg",
            {"group_id": 633, "messages": merged_message},
            None,
        )
        await send_msgs(bot, 633, "group", message)

        # private user should not send in forward
        message = [
            Message(MessageSegment.text("test msg")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
        ]
        ctx.should_call_api(
            "send_private_msg",
            {"user_id": 633, "message": Message(MessageSegment.text("test msg"))},
            None,
        )
        ctx.should_call_api(
            "send_private_msg", {"user_id": 633, "message": message[1]}, None
        )
        ctx.should_call_api(
            "send_private_msg", {"user_id": 633, "message": message[2]}, None
        )
        await send_msgs(bot, 633, "private", message)


async def test_send_merge2_no_queue(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message, MessageSegment
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.send import send_msgs

    plugin_config.bison_use_pic_merge = 2
    plugin_config.bison_use_queue = False

    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=Bot, self_id="8888")
        assert isinstance(bot, Bot)
        message = [
            Message(MessageSegment.text("test msg")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
            Message(MessageSegment.image("https://picsum.photos/200/300")),
        ]
        ctx.should_call_api(
            "get_group_member_info",
            {"group_id": 633, "user_id": 8888, "no_cache": True},
            {"user_id": 8888, "card": "admin", "nickname": "adminuser"},
        )
        merged_message = _merge_messge(
            [
                gen_node(8888, "admin", message[0]),
                gen_node(8888, "admin", message[1]),
                gen_node(8888, "admin", message[2]),
            ]
        )
        ctx.should_call_api(
            "send_group_forward_msg",
            {"group_id": 633, "messages": merged_message},
            None,
        )
        await send_msgs(bot, 633, "group", message)
