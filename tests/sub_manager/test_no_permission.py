from nonebug import App
import pytest

from tests.utils import BotReply, fake_admin_user, fake_group_message_event


@pytest.mark.asyncio
async def test_with_permission(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.platform import platform_manager
    from nonebot_bison.sub_manager import add_sub_matcher, common_platform, no_permission_matcher

    async with app.test_matcher([add_sub_matcher, no_permission_matcher]) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(message=Message("添加订阅"), sender=fake_admin_user, to_me=True)
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            BotReply.add_reply_on_platform(platform_manager, common_platform),
            True,
        )
        ctx.should_pass_rule()
        ctx.should_pass_permission()


@pytest.mark.asyncio
async def test_without_permission(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.sub_manager import add_sub_matcher, no_permission_matcher

    async with app.test_matcher([add_sub_matcher, no_permission_matcher]) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(message=Message("添加订阅"), to_me=True)
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            BotReply.no_permission,
            True,
        )
        ctx.should_pass_rule()
        ctx.should_pass_permission(no_permission_matcher)
        ctx.should_not_pass_permission(add_sub_matcher)
