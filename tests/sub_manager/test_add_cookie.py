import json

from nonebug.app import App
import pytest
from pytest_mock import MockerFixture

from tests.utils import BotReply, fake_private_message_event, fake_superuser


@pytest.mark.usefixtures("_clear_db")
async def test_add_cookie_target_no_cookie(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.sub_manager import add_cookie_target_matcher

    async with app.test_matcher(add_cookie_target_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        from nonebot_plugin_saa import MessageFactory, TargetQQGroup
        from nonebug_saa import should_send_saa

        from nonebot_bison.config import config
        from nonebot_bison.types import Target as T_Target

        target = T_Target("weibo_id")
        platform_name = "weibo"
        await config.add_subscribe(
            TargetQQGroup(group_id=123),
            target=target,
            target_name="weibo_name",
            platform_name=platform_name,
            cats=[],
            tags=[],
        )

        event_1 = fake_private_message_event(
            message=Message("关联cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n1 weibo weibo_name weibo_id\n []\n请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
            ),
            bot,
            event=event_1,
        )
        event_2 = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_2,
            "当前平台暂无可关联的 Cookie，请使用“添加cookie”命令添加或检查已关联的 Cookie",
            True,
        )


@pytest.mark.usefixtures("_clear_db")
@pytest.mark.usefixtures("_patch_weibo_get_cookie_name")
async def test_add_cookie(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import add_cookie_matcher, add_cookie_target_matcher, common_platform

    async with app.test_matcher(add_cookie_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event_1 = fake_private_message_event(
            message=Message("添加cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_1,
            BotReply.add_reply_on_add_cookie(platform_manager, common_platform),
            True,
        )
        event_2 = fake_private_message_event(
            message=Message("全部"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        ctx.should_rejected()
        ctx.should_call_send(
            event_2,
            BotReply.add_reply_on_add_cookie_input_allplatform(platform_manager),
            True,
        )
        event_3 = fake_private_message_event(
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        ctx.should_call_send(event_3, BotReply.add_reply_on_input_cookie)
        event_4_err = fake_private_message_event(
            message=Message("test"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_4_err)
        ctx.should_call_send(
            event_4_err,
            "无效的 Cookie，请检查后重新输入，详情见https://nonebot-bison.netlify.app/usage/cookie.html",
            True,
        )
        ctx.should_rejected()
        event_4_ok = fake_private_message_event(
            message=Message(json.dumps({"cookie": "test"})),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_4_ok)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_4_ok, "已添加 Cookie: weibo: [test_name] 到平台 weibo\n请使用“关联cookie”为 Cookie 关联订阅", True
        )

    async with app.test_matcher(add_cookie_target_matcher) as ctx:
        from nonebot_plugin_saa import MessageFactory, TargetQQGroup
        from nonebug_saa import should_send_saa

        from nonebot_bison.config import config
        from nonebot_bison.types import Target as T_Target

        target = T_Target("weibo_id")
        platform_name = "weibo"
        await config.add_subscribe(
            TargetQQGroup(group_id=123),
            target=target,
            target_name="weibo_name",
            platform_name=platform_name,
            cats=[],
            tags=[],
        )
        bot = ctx.create_bot(base=Bot)
        event_1 = fake_private_message_event(
            message=Message("关联cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n1 weibo weibo_name weibo_id\n []\n请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
            ),
            bot,
            event=event_1,
        )
        event_2_err = fake_private_message_event(
            message=Message("2"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2_err)
        ctx.should_call_send(event_2_err, "序号错误", True)
        ctx.should_rejected()
        event_2_ok = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2_ok)
        ctx.should_pass_rule()
        ctx.should_call_send(event_2_ok, "请选择一个 Cookie，已关联的 Cookie 不会显示\n1. weibo: [test_name]", True)
        event_3_err = fake_private_message_event(
            message=Message("2"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3_err)
        ctx.should_call_send(event_3_err, "序号错误", True)
        ctx.should_rejected()
        event_3_ok = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3_ok)
        ctx.should_pass_rule()
        ctx.should_call_send(event_3_ok, "已关联 Cookie: weibo: [test_name] 到订阅 weibo.com weibo_id", True)


async def test_add_cookie_target_no_target(app: App, mocker: MockerFixture):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.sub_manager import add_cookie_target_matcher

    async with app.test_matcher(add_cookie_target_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event_1 = fake_private_message_event(
            message=Message("关联cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_1,
            "暂无已订阅账号\n请使用“添加订阅”命令添加订阅",
            True,
        )
