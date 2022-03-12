import pytest
import respx
from httpx import Response
from nonebug.app import App

from .platforms.utils import get_json
from .utils import fake_admin_user, fake_group_message_event, BotReply

bot_reply=BotReply()

@pytest.mark.asyncio
async def test_configurable_at_me_true_failed(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config_manager import add_sub_matcher
    from nonebot_bison.plugin_config import plugin_config

    plugin_config.bison_to_me = True
    async with app.test_matcher(add_sub_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(
            message=Message("添加订阅"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule()
        ctx.should_pass_permission()

    async with app.test_matcher(add_sub_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(message=Message("添加订阅"), to_me=True)
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_not_pass_permission()

@pytest.mark.asyncio
async def test_configurable_at_me_false(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.plugin_config import plugin_config

    plugin_config.bison_to_me = False
    async with app.test_matcher(add_sub_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(
            message=Message("添加订阅"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            bot_reply.add_reply_on_platform(platform_manager,common_platform),
            True,
        )
        ctx.should_pass_rule()
        ctx.should_pass_permission()

@pytest.mark.asyncio
@respx.mock
async def test_add_with_target(app: App):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import Config
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager

    config = Config()
    config.user_target.truncate()

    ak_list_router = respx.get(
        "https://m.weibo.cn/api/container/getIndex?containerid=1005056279793937"
    )
    ak_list_router.mock(
        return_value=Response(200, json=get_json("weibo_ak_profile.json"))
    )
    ak_list_bad_router = respx.get(
        "https://m.weibo.cn/api/container/getIndex?containerid=100505000"
    )
    ak_list_bad_router.mock(
        return_value=Response(200, json=get_json("weibo_err_profile.json"))
    )

    async with app.test_matcher(add_sub_matcher) as ctx:
        bot = ctx.create_bot()
        event_1 = fake_group_message_event(
            message=Message("添加订阅"),
            sender=Sender(card="", nickname="test", role="admin"),
            to_me=True,
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_1,
            bot_reply.add_reply_on_platform(platform_manager,common_platform),
            True,
        )
        event_2 = fake_group_message_event(
            message=Message("全部"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_2)
        ctx.should_rejected()
        ctx.should_call_send(
            event_2,
            bot_reply.add_reply_on_platform_input_allplatform(platform_manager),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("weibo"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            bot_reply.add_reply_on_id,
            True,
        )
        event_4_err = fake_group_message_event(
            message=Message("000"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4_err)
        ctx.should_call_send(event_4_err, bot_reply.add_reply_on_id_input_error, True)
        ctx.should_rejected()
        event_4_ok = fake_group_message_event(
            message=Message("6279793937"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4_ok)
        ctx.should_call_send(
            event_4_ok,
            bot_reply.add_reply_on_target_confirm("weibo","明日方舟Arknights","6279793937"),
            True
        )
        ctx.should_call_send(
            event_4_ok,
            bot_reply.add_reply_on_cats(platform_manager,"weibo"),
            True,
        )
        event_5_err = fake_group_message_event(
            message=Message("图文 文字 err"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_5_err)
        ctx.should_call_send(event_5_err, bot_reply.add_reply_on_cats_input_error("err"), True)
        ctx.should_rejected()
        event_5_ok = fake_group_message_event(
            message=Message("图文 文字"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_5_ok)
        ctx.should_call_send(event_5_ok, bot_reply.add_reply_on_tags, True)
        event_6 = fake_group_message_event(
            message=Message("全部标签"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_6)
        ctx.should_call_send(event_6, bot_reply.add_reply_subscribe_success("明日方舟Arknights"), True)
        ctx.should_finished()
    subs = config.list_subscribe(10000, "group")
    assert len(subs) == 1
    sub = subs[0]
    assert sub["target"] == "6279793937"
    assert sub["tags"] == []
    assert sub["cats"] == [platform_manager["weibo"].reverse_category["图文"]] + [
        platform_manager["weibo"].reverse_category["文字"]
    ]
    assert sub["target_type"] == "weibo"
    assert sub["target_name"] == "明日方舟Arknights"

@pytest.mark.asyncio
@respx.mock
async def test_add_with_target_no_cat(app: App):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import Config
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager

    config = Config()
    config.user_target.truncate()

    ncm_router = respx.get("https://music.163.com/api/artist/albums/32540734")
    ncm_router.mock(return_value=Response(200, json=get_json("ncm_siren.json")))

    async with app.test_matcher(add_sub_matcher) as ctx:
        bot = ctx.create_bot()
        event_1 = fake_group_message_event(
            message=Message("添加订阅"),
            sender=Sender(card="", nickname="test", role="admin"),
            to_me=True,
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_1,
            bot_reply.add_reply_on_platform(platform_manager,common_platform),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("ncm-artist"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            bot_reply.add_reply_on_id,
            True,
        )
        event_4_ok = fake_group_message_event(
            message=Message("32540734"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4_ok)
        ctx.should_call_send(
            event_4_ok,
            bot_reply.add_reply_on_target_confirm("ncm-artist","塞壬唱片-MSR","32540734"),
            True
        )
        ctx.should_call_send(event_4_ok, bot_reply.add_reply_subscribe_success("塞壬唱片-MSR"), True)
        ctx.should_finished()
    subs = config.list_subscribe(10000, "group")
    assert len(subs) == 1
    sub = subs[0]
    assert sub["target"] == "32540734"
    assert sub["tags"] == []
    assert sub["cats"] == []
    assert sub["target_type"] == "ncm-artist"
    assert sub["target_name"] == "塞壬唱片-MSR"

@pytest.mark.asyncio
@respx.mock
async def test_add_no_target(app: App):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import Config
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager

    config = Config()
    config.user_target.truncate()

    async with app.test_matcher(add_sub_matcher) as ctx:
        bot = ctx.create_bot()
        event_1 = fake_group_message_event(
            message=Message("添加订阅"),
            sender=Sender(card="", nickname="test", role="admin"),
            to_me=True,
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_1,
            bot_reply.add_reply_on_platform(platform_manager,common_platform),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("arknights"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            bot_reply.add_reply_on_target_confirm("arknights","明日方舟游戏信息","default")
            ,
            True
        )
        ctx.should_call_send(
            event_3,
            bot_reply.add_reply_on_cats(platform_manager,"arknights"),
            True,
        )
        event_4 = fake_group_message_event(
            message=Message("游戏公告"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4)
        ctx.should_call_send(event_4, bot_reply.add_reply_subscribe_success("明日方舟游戏信息"), True)
        ctx.should_finished()
    subs = config.list_subscribe(10000, "group")
    assert len(subs) == 1
    sub = subs[0]
    assert sub["target"] == "default"
    assert sub["tags"] == []
    assert sub["cats"] == [platform_manager["arknights"].reverse_category["游戏公告"]]
    assert sub["target_type"] == "arknights"
    assert sub["target_name"] == "明日方舟游戏信息"

@pytest.mark.asyncio
async def test_platform_name_err(app: App):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import Config
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager

    config = Config()
    config.user_target.truncate()
    async with app.test_matcher(add_sub_matcher) as ctx:
        bot = ctx.create_bot()
        event_1 = fake_group_message_event(
            message=Message("添加订阅"),
            sender=Sender(card="", nickname="test", role="admin"),
            to_me=True,
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_1,
            bot_reply.add_reply_on_platform(platform_manager,common_platform),
            True,
        )
        event_2 = fake_group_message_event(
            message=Message("error"),
            sender=Sender(card="", nickname="test", role="admin"),
        )
        ctx.receive_event(bot, event_2)
        ctx.should_rejected()
        ctx.should_call_send(
            event_2,
            bot_reply.add_reply_on_platform_input_error,
            True,
        )
