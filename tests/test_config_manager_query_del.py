import pytest
import respx
from httpx import Response
from nonebug.app import App

from .platforms.utils import get_json
from .utils import fake_admin_user, fake_group_message_event


@pytest.mark.asyncio
async def test_query_sub(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import config
    from nonebot_bison.config_manager import query_sub_matcher
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.types import Target

    await config.add_subscribe(
        10000,
        "group",
        Target("6279793937"),
        "明日方舟Arknights",
        "weibo",
        [platform_manager["weibo"].reverse_category["图文"]],
        ["明日方舟"],
    )
    async with app.test_matcher(query_sub_matcher) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("查询订阅"), to_me=True)
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_call_send(
            event, Message("订阅的帐号为：\nweibo 明日方舟Arknights 6279793937 [图文] 明日方舟\n"), True
        )


@pytest.mark.asyncio
async def test_del_sub(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import config
    from nonebot_bison.config_manager import del_sub_matcher
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.types import Target

    await config.add_subscribe(
        10000,
        "group",
        Target("6279793937"),
        "明日方舟Arknights",
        "weibo",
        [platform_manager["weibo"].reverse_category["图文"]],
        ["明日方舟"],
    )
    async with app.test_matcher(del_sub_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        assert isinstance(bot, Bot)
        event = fake_group_message_event(
            message=Message("删除订阅"), to_me=True, sender=fake_admin_user
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_call_send(
            event,
            Message(
                "订阅的帐号为：\n1 weibo 明日方舟Arknights 6279793937\n [图文] 明日方舟\n请输入要删除的订阅的序号\n输入'取消'中止"
            ),
            True,
        )
        event_1_err = fake_group_message_event(
            message=Message("2"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_1_err)
        ctx.should_call_send(event_1_err, "删除错误", True)
        ctx.should_rejected()
        event_1_ok = fake_group_message_event(
            message=Message("1"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_1_ok)
        ctx.should_call_send(event_1_ok, "删除成功", True)
        ctx.should_finished()
    subs = await config.list_subscribe(10000, "group")
    assert len(subs) == 0


@pytest.mark.asyncio
async def test_del_empty_sub(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import config
    from nonebot_bison.config_manager import del_sub_matcher
    from nonebot_bison.platform import platform_manager

    async with app.test_matcher(del_sub_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        assert isinstance(bot, Bot)
        event = fake_group_message_event(
            message=Message("删除订阅"), to_me=True, sender=fake_admin_user
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_finished()
        ctx.should_call_send(
            event,
            "暂无已订阅账号\n请使用“添加订阅”命令添加订阅",
            True,
        )
