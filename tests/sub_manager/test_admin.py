from nonebug import App
import pytest

from tests.utils import fake_group_message_event, fake_private_message_event, fake_superuser


@pytest.mark.asyncio
async def test_query_with_superuser_private(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.sub_manager import group_manage_matcher

    async with app.test_matcher(group_manage_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_private_message_event(
            message=Message("群管理"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_call_api("get_group_list", {}, [{"group_id": 101, "group_name": "test group"}])
        ctx.should_call_send(
            event,
            "请选择需要管理的群：\n1. 101 - test group\n请输入左侧序号\n中止操作请输入'取消'",
            True,
        )
        event_1_err = fake_private_message_event(
            message=Message("0"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_1_err)
        ctx.should_call_send(event_1_err, "请输入正确序号", True)
        ctx.should_rejected()
        event_1_ok = fake_private_message_event(
            message=Message("1"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_1_ok)
        ctx.should_call_send(event_1_ok, "请输入需要使用的命令：添加订阅，查询订阅，删除订阅，取消", True)
        event_2_err = fake_private_message_event(
            message=Message("222"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_2_err)
        ctx.should_call_send(event_2_err, "请输入正确的命令", True)
        ctx.should_rejected()
        event_2_ok = fake_private_message_event(
            message=Message("查询订阅"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_2_ok)
        ctx.should_pass_rule()
        ctx.should_pass_permission()


@pytest.mark.asyncio
async def test_query_with_abort_on_idx(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.sub_manager import group_manage_matcher

    async with app.test_matcher(group_manage_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_private_message_event(
            message=Message("群管理"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_call_api("get_group_list", {}, [{"group_id": 101, "group_name": "test group"}])
        ctx.should_call_send(
            event,
            "请选择需要管理的群：\n1. 101 - test group\n请输入左侧序号\n中止操作请输入'取消'",
            True,
        )
        event_abort = fake_private_message_event(
            message=Message("取消"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(event_abort, "已取消", True)
        ctx.should_finished()


async def test_query_with_abort_on_command(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.sub_manager import group_manage_matcher

    async with app.test_matcher(group_manage_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_private_message_event(
            message=Message("群管理"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_call_api("get_group_list", {}, [{"group_id": 101, "group_name": "test group"}])
        ctx.should_call_send(
            event,
            "请选择需要管理的群：\n1. 101 - test group\n请输入左侧序号\n中止操作请输入'取消'",
            True,
        )
        event_1_ok = fake_private_message_event(
            message=Message("1"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_1_ok)
        ctx.should_call_send(event_1_ok, "请输入需要使用的命令：添加订阅，查询订阅，删除订阅，取消", True)
        event_abort = fake_private_message_event(
            message=Message("取消"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(event_abort, "已取消", True)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_query_with_superuser_group_tome(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.sub_manager import group_manage_matcher

    async with app.test_matcher(group_manage_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(
            message=Message("群管理"),
            sender=fake_superuser,
            to_me=True,
            user_id=fake_superuser.user_id,
        )
        ctx.receive_event(bot, event)
        # ctx.should_pass_rule()
        # ctx.should_pass_permission()
        # ctx.should_call_send(event, Message("该功能只支持私聊使用，请私聊Bot"), True)
