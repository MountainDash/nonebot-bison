from httpx import Response
from nonebug.app import App
from nonebug_saa import should_send_saa
import pytest
import respx

from tests.platforms.utils import get_json
from tests.utils import BotReply, fake_admin_user, fake_group_message_event


# 选择platform阶段中止
@pytest.mark.asyncio
@respx.mock
async def test_abort_add_on_platform(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import add_sub_matcher, common_platform

    ak_list_router = respx.get("https://m.weibo.cn/api/container/getIndex?containerid=1005056279793937")
    ak_list_router.mock(return_value=Response(200, json=get_json("weibo_ak_profile.json")))
    ak_list_bad_router = respx.get("https://m.weibo.cn/api/container/getIndex?containerid=100505000")
    ak_list_bad_router.mock(return_value=Response(200, json=get_json("weibo_err_profile.json")))
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
            BotReply.add_reply_on_platform(platform_manager, common_platform),
            True,
        )
        event_abort = fake_group_message_event(
            message=Message("取消"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(
            event_abort,
            BotReply.add_reply_abort,
            True,
        )
        ctx.should_finished()


# 输入id阶段中止
@pytest.mark.asyncio
@respx.mock
async def test_abort_add_on_id(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.weibo import Weibo
    from nonebot_bison.sub_manager import add_sub_matcher, common_platform

    ak_list_router = respx.get("https://m.weibo.cn/api/container/getIndex?containerid=1005056279793937")
    ak_list_router.mock(return_value=Response(200, json=get_json("weibo_ak_profile.json")))
    ak_list_bad_router = respx.get("https://m.weibo.cn/api/container/getIndex?containerid=100505000")
    ak_list_bad_router.mock(return_value=Response(200, json=get_json("weibo_err_profile.json")))
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
            BotReply.add_reply_on_platform(platform_manager, common_platform),
            True,
        )
        event_2 = fake_group_message_event(message=Message("weibo"), sender=fake_admin_user)
        ctx.receive_event(bot, event_2)
        ctx.should_call_send(
            event_2,
            BotReply.add_reply_on_id(Weibo),
            True,
        )
        event_abort = fake_group_message_event(
            message=Message("取消"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(
            event_abort,
            BotReply.add_reply_abort,
            True,
        )
        ctx.should_finished()


# 输入订阅类别阶段中止
@pytest.mark.asyncio
@respx.mock
async def test_abort_add_on_cats(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.weibo import Weibo
    from nonebot_bison.sub_manager import add_sub_matcher, common_platform

    ak_list_router = respx.get("https://m.weibo.cn/api/container/getIndex?type=uid&value=6279793937")
    ak_list_router.mock(return_value=Response(200, json=get_json("weibo_ak_profile.json")))
    ak_list_bad_router = respx.get("https://m.weibo.cn/api/container/getIndex?containerid=100505000")
    ak_list_bad_router.mock(return_value=Response(200, json=get_json("weibo_err_profile.json")))
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
            BotReply.add_reply_on_platform(platform_manager=platform_manager, common_platform=common_platform),
            True,
        )
        event_2 = fake_group_message_event(message=Message("weibo"), sender=fake_admin_user)
        ctx.receive_event(bot, event_2)
        ctx.should_call_send(
            event_2,
            BotReply.add_reply_on_id(Weibo),
            True,
        )
        event_3 = fake_group_message_event(message=Message("6279793937"), sender=fake_admin_user)
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            BotReply.add_reply_on_target_confirm("weibo", "明日方舟Arknights", "6279793937"),
            True,
        )
        ctx.should_call_send(
            event_3,
            BotReply.add_reply_on_cats(platform_manager, "weibo"),
            True,
        )
        event_abort = fake_group_message_event(
            message=Message("取消"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(
            event_abort,
            BotReply.add_reply_abort,
            True,
        )
        ctx.should_finished()


# 输入标签阶段中止
@pytest.mark.asyncio
@respx.mock
async def test_abort_add_on_tag(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.weibo import Weibo
    from nonebot_bison.sub_manager import add_sub_matcher, common_platform

    ak_list_router = respx.get("https://m.weibo.cn/api/container/getIndex?type=uid&value=6279793937")
    ak_list_router.mock(return_value=Response(200, json=get_json("weibo_ak_profile.json")))
    ak_list_bad_router = respx.get("https://m.weibo.cn/api/container/getIndex?containerid=100505000")
    ak_list_bad_router.mock(return_value=Response(200, json=get_json("weibo_err_profile.json")))
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
            BotReply.add_reply_on_platform(platform_manager=platform_manager, common_platform=common_platform),
            True,
        )
        event_2 = fake_group_message_event(message=Message("weibo"), sender=fake_admin_user)
        ctx.receive_event(bot, event_2)
        ctx.should_call_send(
            event_2,
            BotReply.add_reply_on_id(Weibo),
            True,
        )
        event_3 = fake_group_message_event(message=Message("6279793937"), sender=fake_admin_user)
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            BotReply.add_reply_on_target_confirm("weibo", "明日方舟Arknights", "6279793937"),
            True,
        )
        ctx.should_call_send(
            event_3,
            BotReply.add_reply_on_cats(platform_manager, "weibo"),
            True,
        )
        event_4 = fake_group_message_event(message=Message("图文 文字"), sender=fake_admin_user)
        ctx.receive_event(bot, event_4)
        ctx.should_call_send(event_4, BotReply.add_reply_on_tags, True)
        event_abort = fake_group_message_event(
            message=Message("取消"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(
            event_abort,
            BotReply.add_reply_abort,
            True,
        )
        ctx.should_finished()


# 删除订阅阶段中止
@pytest.mark.asyncio
async def test_abort_del_sub(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import del_sub_matcher
    from nonebot_bison.types import Target as T_Target

    await config.add_subscribe(
        TargetQQGroup(group_id=10000),
        T_Target("6279793937"),
        "明日方舟Arknights",
        "weibo",
        [platform_manager["weibo"].reverse_category["图文"]],
        ["明日方舟"],
    )
    async with app.test_matcher(del_sub_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        assert isinstance(bot, Bot)
        event = fake_group_message_event(message=Message("删除订阅"), to_me=True, sender=fake_admin_user)
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n"
                + "1 weibo 明日方舟Arknights 6279793937\n"
                + " [图文] 明日方舟\n"
                + "请输入要删除的订阅的序号\n输入'取消'中止",
            ),
            bot,
            event=event,
        )
        event_abort = fake_group_message_event(message=Message("取消"), sender=fake_admin_user)
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(event_abort, "删除中止", True)
        ctx.should_finished()
    subs = await config.list_subscribe(TargetQQGroup(group_id=10000))
    assert subs
