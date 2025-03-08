from nonebug.app import App
from nonebug_saa import should_send_saa
import pytest

from tests.utils import fake_admin_user, fake_group_message_event


@pytest.mark.asyncio
async def test_query_sub(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11 import Bot, Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import query_sub_matcher
    from nonebot_bison.types import Target

    await config.add_subscribe(
        TargetQQGroup(group_id=10000),
        Target("6279793937"),
        "明日方舟Arknights",
        "weibo",
        [platform_manager["weibo"].reverse_category["图文"]],
        ["明日方舟"],
    )
    async with app.test_matcher(query_sub_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)

        event = fake_group_message_event(message=Message("查询订阅"), to_me=True)
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        should_send_saa(
            ctx,
            MessageFactory("订阅的帐号为：\nweibo 明日方舟Arknights 6279793937\n [图文] 明日方舟\n"),
            bot,
            event=event,
        )


@pytest.mark.asyncio
async def test_query_no_exsits_sub(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11 import Bot, Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import query_sub_matcher
    from nonebot_bison.types import Target

    platform_manager["no_exsits_platform"] = platform_manager["weibo"]
    await config.add_subscribe(
        TargetQQGroup(group_id=10000),
        Target("6279793937"),
        "明日方舟Arknights",
        "no_exsits_platform",
        [platform_manager["weibo"].reverse_category["图文"]],
        ["明日方舟"],
    )
    del platform_manager["no_exsits_platform"]
    async with app.test_matcher(query_sub_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)

        event = fake_group_message_event(message=Message("查询订阅"), to_me=True)
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        should_send_saa(
            ctx,
            MessageFactory(
                "订阅的帐号为：\nno_exsits_platform 明日方舟Arknights 6279793937\n"
                + " （平台 no_exsits_platform 已失效，请删除此订阅）\n"
            ),
            bot,
            event=event,
        )


@pytest.mark.asyncio
async def test_del_sub(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import del_sub_matcher
    from nonebot_bison.types import Target

    await config.add_subscribe(
        TargetQQGroup(group_id=10000),
        Target("6279793937"),
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
        event_1_err = fake_group_message_event(message=Message("2"), sender=fake_admin_user)
        ctx.receive_event(bot, event_1_err)
        ctx.should_call_send(event_1_err, "删除错误", True)
        ctx.should_rejected()
        event_1_ok = fake_group_message_event(message=Message("1"), sender=fake_admin_user)
        ctx.receive_event(bot, event_1_ok)
        ctx.should_call_send(event_1_ok, "删除成功", True)
        ctx.should_finished()
    subs = await config.list_subscribe(TargetQQGroup(group_id=10000))
    assert len(subs) == 0


@pytest.mark.asyncio
async def test_del_no_exsits_sub(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup

    from nonebot_bison.config import config
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import del_sub_matcher
    from nonebot_bison.types import Target

    platform_manager["no_exsits_platform"] = platform_manager["weibo"]
    await config.add_subscribe(
        TargetQQGroup(group_id=10000),
        Target("6279793937"),
        "明日方舟Arknights",
        "no_exsits_platform",
        [platform_manager["weibo"].reverse_category["图文"]],
        ["明日方舟"],
    )
    del platform_manager["no_exsits_platform"]
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
                + "1 no_exsits_platform 明日方舟Arknights 6279793937\n"
                + " （平台 no_exsits_platform 已失效，请删除此订阅）\n"
                + "请输入要删除的订阅的序号\n输入'取消'中止",
            ),
            bot,
            event=event,
        )
        event_1_err = fake_group_message_event(message=Message("2"), sender=fake_admin_user)
        ctx.receive_event(bot, event_1_err)
        ctx.should_call_send(event_1_err, "删除错误", True)
        ctx.should_rejected()
        event_1_ok = fake_group_message_event(message=Message("1"), sender=fake_admin_user)
        ctx.receive_event(bot, event_1_ok)
        ctx.should_call_send(event_1_ok, "删除成功", True)
        ctx.should_finished()
    subs = await config.list_subscribe(TargetQQGroup(group_id=10000))
    assert len(subs) == 0


@pytest.mark.asyncio
async def test_del_empty_sub(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.sub_manager import del_sub_matcher

    async with app.test_matcher(del_sub_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        assert isinstance(bot, Bot)
        event = fake_group_message_event(message=Message("删除订阅"), to_me=True, sender=fake_admin_user)
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_finished()
        ctx.should_call_send(
            event,
            "暂无已订阅账号\n请使用“添加订阅”命令添加订阅",
            True,
        )
