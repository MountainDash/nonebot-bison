from email import message

import pytest
import respx
from httpx import Response
from nonebug.app import App

from .platforms.utils import get_json
from .utils import BotReply, fake_admin_user, fake_group_message_event


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
            Message(BotReply.add_reply_on_platform(platform_manager, common_platform)),
            True,
        )
        ctx.should_pass_rule()
        ctx.should_pass_permission()


@pytest.mark.asyncio
@respx.mock
async def test_add_with_target(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import config
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.weibo import Weibo

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
                BotReply.add_reply_on_platform(
                    platform_manager=platform_manager, common_platform=common_platform
                )
            ),
            True,
        )
        event_2 = fake_group_message_event(
            message=Message("全部"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_2)
        ctx.should_rejected()
        ctx.should_call_send(
            event_2,
            BotReply.add_reply_on_platform_input_allplatform(platform_manager),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("weibo"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            Message(BotReply.add_reply_on_id(Weibo)),
            True,
        )
        event_4_err = fake_group_message_event(
            message=Message("000"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4_err)
        ctx.should_call_send(event_4_err, BotReply.add_reply_on_id_input_error, True)
        ctx.should_rejected()
        event_4_ok = fake_group_message_event(
            message=Message("6279793937"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4_ok)
        ctx.should_call_send(
            event_4_ok,
            BotReply.add_reply_on_target_confirm(
                "weibo", "明日方舟Arknights", "6279793937"
            ),
            True,
        )
        ctx.should_call_send(
            event_4_ok,
            Message(BotReply.add_reply_on_cats(platform_manager, "weibo")),
            True,
        )
        event_5_err = fake_group_message_event(
            message=Message("图文 文字 err"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_5_err)
        ctx.should_call_send(
            event_5_err, BotReply.add_reply_on_cats_input_error("err"), True
        )
        ctx.should_rejected()
        event_5_ok = fake_group_message_event(
            message=Message("图文 文字"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_5_ok)
        ctx.should_call_send(event_5_ok, Message(BotReply.add_reply_on_tags), True)
        event_6_more_info = fake_group_message_event(
            message=Message("详情"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_6_more_info)
        ctx.should_call_send(
            event_6_more_info, BotReply.add_reply_on_tags_need_more_info, True
        )
        ctx.should_rejected()
        event_6_ok = fake_group_message_event(
            message=Message("全部标签"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_6_ok)
        ctx.should_call_send(
            event_6_ok, BotReply.add_reply_subscribe_success("明日方舟Arknights"), True
        )
        ctx.should_finished()
    subs = await config.list_subscribe(10000, "group")
    assert len(subs) == 1
    sub = subs[0]
    assert sub.target.target == "6279793937"
    assert sub.tags == []
    assert sub.categories == [platform_manager["weibo"].reverse_category["图文"]] + [
        platform_manager["weibo"].reverse_category["文字"]
    ]
    assert sub.target.platform_name == "weibo"
    assert sub.target.target_name == "明日方舟Arknights"


@pytest.mark.asyncio
@respx.mock
async def test_add_with_target_no_cat(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import config
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.ncm_artist import NcmArtist

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
            Message(BotReply.add_reply_on_platform(platform_manager, common_platform)),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("ncm-artist"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            Message(BotReply.add_reply_on_id(NcmArtist)),
            True,
        )
        event_4_ok = fake_group_message_event(
            message=Message("32540734"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4_ok)
        ctx.should_call_send(
            event_4_ok,
            BotReply.add_reply_on_target_confirm("ncm-artist", "塞壬唱片-MSR", "32540734"),
            True,
        )
        ctx.should_call_send(
            event_4_ok, BotReply.add_reply_subscribe_success("塞壬唱片-MSR"), True
        )
        ctx.should_finished()
    subs = await config.list_subscribe(10000, "group")
    assert len(subs) == 1
    sub = subs[0]
    assert sub.target.target == "32540734"
    assert sub.tags == []
    assert sub.categories == []
    assert sub.target.platform_name == "ncm-artist"
    assert sub.target.target_name == "塞壬唱片-MSR"


@pytest.mark.asyncio
@respx.mock
async def test_add_no_target(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import config
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager

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
            Message(BotReply.add_reply_on_platform(platform_manager, common_platform)),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("arknights"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            Message(BotReply.add_reply_on_cats(platform_manager, "arknights")),
            True,
        )
        event_4 = fake_group_message_event(
            message=Message("游戏公告"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4)
        ctx.should_call_send(
            event_4, BotReply.add_reply_subscribe_success("明日方舟游戏信息"), True
        )
        ctx.should_finished()
    subs = await config.list_subscribe(10000, "group")
    assert len(subs) == 1
    sub = subs[0]
    assert sub.target.target == "default"
    assert sub.tags == []
    assert sub.categories == [platform_manager["arknights"].reverse_category["游戏公告"]]
    assert sub.target.platform_name == "arknights"
    assert sub.target.target_name == "明日方舟游戏信息"


@pytest.mark.asyncio
async def test_platform_name_err(app: App, db_migration):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager

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
            Message(BotReply.add_reply_on_platform(platform_manager, common_platform)),
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
            BotReply.add_reply_on_platform_input_error,
            True,
        )


@pytest.mark.asyncio
@respx.mock
async def test_add_with_get_id(app: App, db_migration):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message, MessageSegment
    from nonebot_bison.config import config
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.weibo import Weibo

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
                BotReply.add_reply_on_platform(
                    platform_manager=platform_manager, common_platform=common_platform
                )
            ),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("weibo"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        ctx.should_call_send(
            event_3,
            Message(BotReply.add_reply_on_id(Weibo)),
            True,
        )
        event_4_query = fake_group_message_event(
            message=Message("查询"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_4_query)
        ctx.should_rejected()
        ctx.should_call_send(
            event_4_query,
            Message([MessageSegment(*BotReply.add_reply_on_id_input_search())]),
            True,
        )
        """
        关于：Message([MessageSegment(*BotReply.add_reply_on_id_input_search())])
        鬼知道为什么要在这里这样写，
        没有[]的话assert不了(should_call_send使用[MessageSegment(...)]的格式进行比较)
        不在这里MessageSegment()的话也assert不了(指不能让add_reply_on_id_input_search直接返回一个MessageSegment对象)
        amen
        """
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
    subs = await config.list_subscribe(10000, "group")
    assert len(subs) == 0


@pytest.mark.asyncio
@respx.mock
async def test_add_with_bilibili_target_parser(app: App, init_scheduler):
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11.message import Message
    from nonebot_bison.config import config
    from nonebot_bison.config_manager import add_sub_matcher, common_platform
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.bilibili import Bilibili

    ak_list_router = respx.get(
        "https://api.bilibili.com/x/space/acc/info?mid=161775300"
    )
    ak_list_router.mock(
        return_value=Response(200, json=get_json("bilibili_arknights_profile.json"))
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
                BotReply.add_reply_on_platform(
                    platform_manager=platform_manager, common_platform=common_platform
                )
            ),
            True,
        )
        event_2 = fake_group_message_event(
            message=Message("全部"), sender=Sender(card="", nickname="test", role="admin")
        )
        ctx.receive_event(bot, event_2)
        ctx.should_rejected()
        ctx.should_call_send(
            event_2,
            BotReply.add_reply_on_platform_input_allplatform(platform_manager),
            True,
        )
        event_3 = fake_group_message_event(
            message=Message("bilibili"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_3)
        assert Bilibili.parse_target_promot
        ctx.should_call_send(
            event_3,
            Message(BotReply.add_reply_on_id(Bilibili)),
            True,
        )
        event_4_err1 = fake_group_message_event(
            message=Message(
                "https://live.bilibili.com/5555734?broadcast_type=0&is_room_feed=1&spm_id_from=333.999.0.0"
            ),
            sender=fake_admin_user,
        )
        ctx.receive_event(bot, event_4_err1)
        ctx.should_call_send(
            event_4_err1, BotReply.add_reply_on_target_parse_input_error, True
        )
        ctx.should_rejected()

        event_4_err1 = fake_group_message_event(
            message=Message(
                "https://space.bilibili.com/ark161775300?from=search&seid=13051774060625135297&spm_id_from=333.337.0.0"
            ),
            sender=fake_admin_user,
        )
        ctx.receive_event(bot, event_4_err1)
        ctx.should_call_send(
            event_4_err1, BotReply.add_reply_on_target_parse_input_error, True
        )
        ctx.should_rejected()

        event_4_ok = fake_group_message_event(
            message=Message(
                "https://space.bilibili.com/161775300?from=search&seid=13051774060625135297&spm_id_from=333.337.0.0"
            ),
            sender=fake_admin_user,
        )
        ctx.receive_event(bot, event_4_ok)
        ctx.should_call_send(
            event_4_ok,
            BotReply.add_reply_on_target_confirm("bilibili", "明日方舟", "161775300"),
            True,
        )
        ctx.should_call_send(
            event_4_ok,
            Message(BotReply.add_reply_on_cats(platform_manager, "bilibili")),
            True,
        )
        event_5_ok = fake_group_message_event(
            message=Message("视频"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_5_ok)
        ctx.should_call_send(event_5_ok, Message(BotReply.add_reply_on_tags), True)
        event_6 = fake_group_message_event(
            message=Message("全部标签"), sender=fake_admin_user
        )
        ctx.receive_event(bot, event_6)
        ctx.should_call_send(
            event_6, BotReply.add_reply_subscribe_success("明日方舟"), True
        )
        ctx.should_finished()
    subs = await config.list_subscribe(10000, "group")
    assert len(subs) == 1
    sub = subs[0]
    assert sub.target.target == "161775300"
    assert sub.tags == []
    assert sub.categories == [platform_manager["bilibili"].reverse_category["视频"]]
    assert sub.target.platform_name == "bilibili"
    assert sub.target.target_name == "明日方舟"
