import json

from nonebug.app import App
import pytest

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
                "请输入想要关联 Cookie 的平台，目前支持，请输入冒号左边的名称：\nbilibili: "
                'B站\nrss: Rss\nweibo: 新浪微博\n中止关联过程请输入："取消"'
            ),
            bot,
            event=event_1,
        )
        event_2 = fake_private_message_event(
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n1 weibo_name weibo_id\n []\n请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
            ),
            bot,
            event=event_2,
        )
        event_3 = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_3,
            '当前平台暂无可关联的 Cookie，请使用"添加cookie"命令添加或检查已关联的 Cookie',
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

        # Construct expected message to match source code format
        expected_message = "已添加 Cookie: weibo: [test_name] 到平台 weibo" + "\n请使用“关联cookie”为 Cookie 关联订阅"
        ctx.should_call_send(event_4_ok, expected_message, True)

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
                "请输入想要关联 Cookie 的平台，目前支持，请输入冒号左边的名称：\nbilibili: "
                'B站\nrss: Rss\nweibo: 新浪微博\n中止关联过程请输入："取消"'
            ),
            bot,
            event=event_1,
        )
        event_2 = fake_private_message_event(
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n1 weibo_name weibo_id\n []\n请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
            ),
            bot,
            event=event_2,
        )
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
        ctx.should_call_send(event_3_ok, "请选择一个 Cookie，已关联的 Cookie 不会显示\n1. weibo: [test_name]", True)
        event_4_err = fake_private_message_event(
            message=Message("2"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_4_err)
        ctx.should_call_send(event_4_err, "序号错误", True)
        ctx.should_rejected()
        event_4_ok = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_4_ok)
        ctx.should_pass_rule()
        ctx.should_call_send(event_4_ok, "已关联 Cookie: weibo: [test_name] 到订阅 weibo.com weibo_id", True)


@pytest.mark.usefixtures("_clear_db")
@pytest.mark.usefixtures("_patch_weibo_get_cookie_name")
async def test_add_cookie_target_multiple_subscriptions(app: App):
    """Test cookie target association with multiple subscriptions"""
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup
    from nonebug_saa import should_send_saa

    from nonebot_bison.config import config
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import add_cookie_matcher, add_cookie_target_matcher, common_platform
    from nonebot_bison.types import Target as T_Target

    # Create multiple subscriptions for the same platform
    target1 = T_Target("weibo_id_1")
    target2 = T_Target("weibo_id_2")
    platform_name = "weibo"

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=target1,
        target_name="weibo_name_1",
        platform_name=platform_name,
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=target2,
        target_name="weibo_name_2",
        platform_name=platform_name,
        cats=[],
        tags=[],
    )

    # Add cookie first
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
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        ctx.should_call_send(event_2, BotReply.add_reply_on_input_cookie)
        event_3 = fake_private_message_event(
            message=Message(json.dumps({"cookie": "test"})),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        expected_message = "已添加 Cookie: weibo: [test_name] 到平台 weibo\n请使用“关联cookie”为 Cookie 关联订阅"
        ctx.should_call_send(event_3, expected_message, True)

    # Test cookie target association
    async with app.test_matcher(add_cookie_target_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)

        event_1 = fake_private_message_event(
            message=Message("关联cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "请输入想要关联 Cookie 的平台，目前支持，请输入冒号左边的名称：\nbilibili: B站\nrss: Rss\n"
                'weibo: 新浪微博\n中止关联过程请输入："取消"'
            ),
            bot,
            event=event_1,
        )

        event_2 = fake_private_message_event(
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n1 weibo_name_1 weibo_id_1\n []\n2 weibo_name_2 weibo_id_2"
                "\n []\n3 全部 (关联该平台下的所有订阅)\n请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
            ),
            bot,
            event=event_2,
        )

        # Test invalid subscription index
        event_3_err = fake_private_message_event(
            message=Message("99"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3_err)
        ctx.should_call_send(event_3_err, "序号错误", True)
        ctx.should_rejected()

        # Test valid subscription index
        event_3_ok = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3_ok)
        ctx.should_pass_rule()
        ctx.should_call_send(event_3_ok, "请选择一个 Cookie，已关联的 Cookie 不会显示\n1. weibo: [test_name]", True)

        # Test invalid cookie index
        event_4_err = fake_private_message_event(
            message=Message("99"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_4_err)
        ctx.should_call_send(event_4_err, "序号错误", True)
        ctx.should_rejected()

        # Test valid cookie index
        event_4_ok = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_4_ok)
        ctx.should_pass_rule()
        ctx.should_call_send(event_4_ok, "已关联 Cookie: weibo: [test_name] 到订阅 weibo.com weibo_id_1", True)


@pytest.mark.usefixtures("_clear_db")
async def test_add_cookie_target_no_available_cookies(app: App):
    """Test cookie association when no cookies are available"""
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup
    from nonebug_saa import should_send_saa

    from nonebot_bison.config import config
    from nonebot_bison.sub_manager import add_cookie_target_matcher
    from nonebot_bison.types import Target as T_Target

    # Create subscription without adding any cookies
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

    async with app.test_matcher(add_cookie_target_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)

        event_1 = fake_private_message_event(
            message=Message("关联cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "请输入想要关联 Cookie 的平台，目前支持，请输入冒号左边的名称：\nbilibili: "
                'B站\nrss: Rss\nweibo: 新浪微博\n中止关联过程请输入："取消"'
            ),
            bot,
            event=event_1,
        )

        event_2 = fake_private_message_event(
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n1 weibo_name weibo_id\n []\n请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
            ),
            bot,
            event=event_2,
        )

        event_3 = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_3,
            '当前平台暂无可关联的 Cookie，请使用"添加cookie"命令添加或检查已关联的 Cookie',
            True,
        )


@pytest.mark.usefixtures("_clear_db")
@pytest.mark.usefixtures("_patch_weibo_get_cookie_name")
async def test_add_cookie_already_associated(app: App):
    """Test cookie association when cookie is already associated"""
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup
    from nonebug_saa import should_send_saa

    from nonebot_bison.config import config
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import add_cookie_matcher, add_cookie_target_matcher, common_platform
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

    # Add cookie and associate it
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
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        ctx.should_call_send(event_2, BotReply.add_reply_on_input_cookie)
        event_3 = fake_private_message_event(
            message=Message(json.dumps({"cookie": "test"})),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        expected_message = "已添加 Cookie: weibo: [test_name] 到平台 weibo\n请使用“关联cookie”为 Cookie 关联订阅"
        ctx.should_call_send(event_3, expected_message, True)

    # Associate the cookie
    async with app.test_matcher(add_cookie_target_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event_1 = fake_private_message_event(
            message=Message("关联cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "请输入想要关联 Cookie 的平台，目前支持，请输入冒号左边的名称：\nbilibili: "
                'B站\nrss: Rss\nweibo: 新浪微博\n中止关联过程请输入："取消"'
            ),
            bot,
            event=event_1,
        )
        event_2 = fake_private_message_event(
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n1 weibo_name weibo_id\n []\n请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
            ),
            bot,
            event=event_2,
        )
        event_3 = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        ctx.should_call_send(event_3, "请选择一个 Cookie，已关联的 Cookie 不会显示\n1. weibo: [test_name]", True)
        event_4 = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_4)
        ctx.should_pass_rule()
        ctx.should_call_send(event_4, "已关联 Cookie: weibo: [test_name] 到订阅 weibo.com weibo_id", True)

    # Try to associate again - should show no available cookies
    async with app.test_matcher(add_cookie_target_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event_1 = fake_private_message_event(
            message=Message("关联cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "请输入想要关联 Cookie 的平台，目前支持，请输入冒号左边的名称：\nbilibili: "
                'B站\nrss: Rss\nweibo: 新浪微博\n中止关联过程请输入："取消"'
            ),
            bot,
            event=event_1,
        )

        event_2 = fake_private_message_event(
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n1 weibo_name weibo_id\n []\n  关联的 Cookie：\n  \tweibo: [test_name]"
                "\n请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
            ),
            bot,
            event=event_2,
        )

        event_3 = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_3,
            '当前平台暂无可关联的 Cookie，请使用"添加cookie"命令添加或检查已关联的 Cookie',
            True,
        )


@pytest.mark.usefixtures("_clear_db")
@pytest.mark.usefixtures("_patch_weibo_get_cookie_name")
async def test_add_cookie_batch_association(app: App):
    """Test batch cookie association with multiple subscriptions"""
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup
    from nonebug_saa import should_send_saa

    from nonebot_bison.config import config
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import (
        add_cookie_matcher,
        add_cookie_target_matcher,
        common_platform,
        del_cookie_target_matcher,
    )
    from nonebot_bison.types import Target as T_Target

    # Create multiple subscriptions for batch testing
    target1 = T_Target("weibo_id_1")
    target2 = T_Target("weibo_id_2")
    target3 = T_Target("weibo_id_3")
    platform_name = "weibo"

    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=target1,
        target_name="weibo_name_1",
        platform_name=platform_name,
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=target2,
        target_name="weibo_name_2",
        platform_name=platform_name,
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        TargetQQGroup(group_id=123),
        target=target3,
        target_name="weibo_name_3",
        platform_name=platform_name,
        cats=[],
        tags=[],
    )

    # Add cookie first
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
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        ctx.should_call_send(event_2, BotReply.add_reply_on_input_cookie)
        event_3 = fake_private_message_event(
            message=Message(json.dumps({"cookie": "test"})),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        expected_message = "已添加 Cookie: weibo: [test_name] 到平台 weibo\n请使用“关联cookie”为 Cookie 关联订阅"
        ctx.should_call_send(event_3, expected_message, True)

    # Test batch cookie association
    async with app.test_matcher(add_cookie_target_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)

        event_1 = fake_private_message_event(
            message=Message("关联cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "请输入想要关联 Cookie 的平台，目前支持，请输入冒号左边的名称：\nbilibili: B站\nrss: Rss\n"
                'weibo: 新浪微博\n中止关联过程请输入："取消"'
            ),
            bot,
            event=event_1,
        )

        event_2 = fake_private_message_event(
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\n1 weibo_name_1 weibo_id_1\n []\n2 weibo_name_2 weibo_id_2"
                "\n []\n3 weibo_name_3 weibo_id_3\n []\n4 全部 (关联该平台下的所有订阅)"
                "\n请输入要关联 cookie 的订阅的序号\n输入'取消'中止"
            ),
            bot,
            event=event_2,
        )

        # Select batch mode (option 4 for "全部")
        event_3 = fake_private_message_event(
            message=Message("4"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        ctx.should_call_send(
            event_3,
            "请选择一个 Cookie 关联到该平台的所有 3 个订阅，已关联的 Cookie 不会显示\n1. weibo: [test_name]",
            True,
        )

        # Select the cookie for batch association
        event_4 = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_4)
        ctx.should_pass_rule()
        ctx.should_call_send(event_4, "已关联 Cookie: weibo: [test_name] 到 3 个订阅", True)

    # Test batch cookie deassociation (取消关联)
    async with app.test_matcher(del_cookie_target_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)

        # Start deassociation process
        event_1 = fake_private_message_event(
            message=Message("取消关联cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                '请输入想要取消关联 Cookie 的平台，目前有关联的平台：\nweibo: 新浪微博\n中止取消关联过程请输入："取消"'
            ),
            bot,
            event=event_1,
        )

        # Select platform (weibo)
        event_2 = fake_private_message_event(
            message=Message("weibo"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        should_send_saa(
            ctx,
            MessageFactory(
                "新浪微博平台已关联的 Cookie：\n"
                "1. weibo_name_1 weibo: [test_name]\n"
                "2. weibo_name_2 weibo: [test_name]\n"
                "3. weibo_name_3 weibo: [test_name]\n"
                "请输入要取消关联的序号（多个序号用空格分隔）\n输入'取消'中止"
            ),
            bot,
            event=event_2,
        )

        # Select multiple targets for batch deassociation (1 2 3)
        event_3 = fake_private_message_event(
            message=Message("1 2 3"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_3)
        ctx.should_pass_rule()
        ctx.should_call_send(event_3, "批量取消关联成功，共处理 3 个关联", True)
