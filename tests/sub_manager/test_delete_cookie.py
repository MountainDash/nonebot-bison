import json

from nonebug.app import App
import pytest

from tests.utils import fake_private_message_event, fake_superuser


@pytest.mark.usefixtures("_clear_db")
async def test_del_cookie(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup
    from nonebug_saa import should_send_saa

    from nonebot_bison.config import config
    from nonebot_bison.config.db_model import Cookie
    from nonebot_bison.sub_manager import del_cookie_matcher
    from nonebot_bison.types import Target as T_Target

    async with app.test_matcher(del_cookie_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_private_message_event(
            message=Message("删除cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_call_send(event, "暂无已添加的 Cookie\n请使用“添加cookie”命令添加", True)

    async with app.test_matcher(del_cookie_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
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
        await config.add_cookie(Cookie(content=json.dumps({"cookie": "test"}), site_name="weibo.com"))

        event_1 = fake_private_message_event(
            message=Message("删除cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        should_send_saa(
            ctx,
            MessageFactory(
                "已添加的 Cookie 为：\n1 weibo.com unnamed cookie 0个关联\n请输入要删除的 Cookie 的序号\n输入'取消'中止"
            ),
            bot,
            event=event_1,
        )
        event_2 = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_call_send(event_2, "删除成功", True)


@pytest.mark.usefixtures("_clear_db")
@pytest.mark.usefixtures("_patch_weibo_get_cookie_name")
async def test_del_cookie_err(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup
    from nonebug_saa import should_send_saa

    from nonebot_bison.config import config
    from nonebot_bison.config.db_model import Cookie
    from nonebot_bison.sub_manager import del_cookie_matcher
    from nonebot_bison.types import Target as T_Target

    async with app.test_matcher(del_cookie_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_private_message_event(
            message=Message("删除cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        ctx.should_call_send(event, "暂无已添加的 Cookie\n请使用“添加cookie”命令添加", True)

    async with app.test_matcher(del_cookie_matcher) as ctx:
        bot = ctx.create_bot(base=Bot)
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
        await config.add_cookie(Cookie(content=json.dumps({"cookie": "test"}), site_name="weibo.com"))
        cookies = await config.get_cookie(is_anonymous=False)
        await config.add_cookie_target(target, platform_name, cookies[0].id)

        event_1 = fake_private_message_event(
            message=Message("删除cookie"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_1)
        ctx.should_pass_rule()
        ctx.should_pass_permission()
        should_send_saa(
            ctx,
            MessageFactory(
                "已添加的 Cookie 为：\n1 weibo.com unnamed cookie 1个关联\n请输入要删除的 Cookie 的序号\n输入'取消'中止"
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

        event_2 = fake_private_message_event(
            message=Message("1"), sender=fake_superuser, to_me=True, user_id=fake_superuser.user_id
        )
        ctx.receive_event(bot, event_2)
        ctx.should_pass_rule()
        ctx.should_call_send(event_2, "只能删除未关联的 Cookie，请使用“取消关联cookie”命令取消关联", True)
        ctx.should_call_send(event_2, "删除错误", True)
        ctx.should_rejected()
