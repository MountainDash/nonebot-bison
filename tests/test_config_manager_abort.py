import pytest
import respx
from httpx import Response
from nonebug.app import App

from .platforms.utils import get_json
from .utils import fake_admin_user, fake_group_message_event


# 选择platform阶段中止
@pytest.mark.asyncio
@respx.mock
async def test_abort_add_on_platform(app: App):
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
            Message(
                "请输入想要订阅的平台，目前支持，请输入冒号左边的名称：\n"
                + "".join(
                    [
                        "{}：{}\n".format(
                            platform_name, platform_manager[platform_name].name
                        )
                        for platform_name in common_platform
                    ]
                )
                + "要查看全部平台请输入：“全部”\n中止订阅过程请输入：“取消”"
            ),
            True,
        )
        event_abort = fake_group_message_event(
            message=Message("取消"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(
            event_abort,
            "已中止订阅",
            True,
        )
        ctx.should_finished()


# 输入id阶段中止
@pytest.mark.asyncio
@respx.mock
async def test_abort_add_on_id(app: App):
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
            Message(
                "请输入想要订阅的平台，目前支持，请输入冒号左边的名称：\n"
                + "".join(
                    [
                        "{}：{}\n".format(
                            platform_name, platform_manager[platform_name].name
                        )
                        for platform_name in common_platform
                    ]
                )
                + "要查看全部平台请输入：“全部”\n中止订阅过程请输入：“取消”"
            ),
            True,
        )
        event_2 = fake_group_message_event(
            message=Message("weibo"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_2)
        ctx.should_call_send(
            event_2,
            Message(
                "请输入订阅用户的id，详情查阅https://nonebot-bison.vercel.app/usage/#%E6%89%80%E6%94%AF%E6%8C%81%E5%B9%B3%E5%8F%B0%E7%9A%84uid"
            ),
            True,
        )
        event_abort = fake_group_message_event(
            message=Message("取消"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(
            event_abort,
            "已中止订阅",
            True,
        )
        ctx.should_finished()


# 输入订阅类别阶段中止
@pytest.mark.asyncio
@respx.mock
async def test_abort_add_on_cats(app: App):
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
            Message(
                "请输入想要订阅的平台，目前支持，请输入冒号左边的名称：\n"
                + "".join(
                    [
                        "{}：{}\n".format(
                            platform_name, platform_manager[platform_name].name
                        )
                        for platform_name in common_platform
                    ]
                )
                + "要查看全部平台请输入：“全部”\n中止订阅过程请输入：“取消”"
            ),
            True,
        )
        event_2 = fake_group_message_event(
            message=Message("weibo"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_2)
        ctx.should_call_send(
            event_2,
            Message(
                "请输入订阅用户的id，详情查阅https://nonebot-bison.vercel.app/usage/#%E6%89%80%E6%94%AF%E6%8C%81%E5%B9%B3%E5%8F%B0%E7%9A%84uid"
            ),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("6279793937"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            Message(
                "请输入要订阅的类别，以空格分隔，支持的类别有：{}".format(
                    " ".join(list(platform_manager["weibo"].categories.values()))
                )
            ),
            True,
        )
        event_abort = fake_group_message_event(
            message=Message("取消"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(
            event_abort,
            "已中止订阅",
            True,
        )
        ctx.should_finished()


# 输入标签阶段中止
@pytest.mark.asyncio
@respx.mock
async def test_abort_add_on_tag(app: App):
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
            Message(
                "请输入想要订阅的平台，目前支持，请输入冒号左边的名称：\n"
                + "".join(
                    [
                        "{}：{}\n".format(
                            platform_name, platform_manager[platform_name].name
                        )
                        for platform_name in common_platform
                    ]
                )
                + "要查看全部平台请输入：“全部”\n中止订阅过程请输入：“取消”"
            ),
            True,
        )
        event_2 = fake_group_message_event(
            message=Message("weibo"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_2)
        ctx.should_call_send(
            event_2,
            Message(
                "请输入订阅用户的id，详情查阅https://nonebot-bison.vercel.app/usage/#%E6%89%80%E6%94%AF%E6%8C%81%E5%B9%B3%E5%8F%B0%E7%9A%84uid"
            ),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("6279793937"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            Message(
                "请输入要订阅的类别，以空格分隔，支持的类别有：{}".format(
                    " ".join(list(platform_manager["weibo"].categories.values()))
                )
            ),
            True,
        )
        event_4 = fake_group_message_event(
            message=Message("图文 文字"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4)
        ctx.should_call_send(event_4, Message('请输入要订阅的tag，订阅所有tag输入"全部标签"'), True)
        event_abort = fake_group_message_event(
            message=Message("取消"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_abort)
        ctx.should_call_send(
            event_abort,
            "已中止订阅",
            True,
        )
        ctx.should_finished()
