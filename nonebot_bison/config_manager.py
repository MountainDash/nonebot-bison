import asyncio
from datetime import datetime
from typing import Annotated, Optional, Type, cast

from nonebot import logger, on_command
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v11.utils import unescape
from nonebot.internal.params import ArgStr
from nonebot.internal.rule import Rule
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, Depends, EventPlainText, EventToMe
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot_plugin_saa import (
    MessageFactory,
    PlatformTarget,
    TargetQQGroup,
    extract_target,
)

from .apis import check_sub_target
from .config import config
from .config.db_config import SubscribeDupException
from .platform import Platform, platform_manager
from .plugin_config import plugin_config
from .types import Category, Target
from .utils import parse_text


def _configurable_to_me(to_me: bool = EventToMe()):
    if plugin_config.bison_to_me:
        return to_me
    else:
        return True


configurable_to_me = Rule(_configurable_to_me)


common_platform = [
    p.platform_name
    for p in filter(
        lambda platform: platform.enabled and platform.is_common,
        platform_manager.values(),
    )
]


def ensure_user_info(matcher: Type[Matcher]):
    async def _check_user_info(state: T_State):
        if not state.get("target_user_info"):
            await matcher.finish(
                "No target_user_info set, this shouldn't happen, please issue"
            )

    return _check_user_info


async def set_target_user_info(event: Event, state: T_State):
    user = extract_target(event)
    state["target_user_info"] = user


def gen_handle_cancel(matcher: Type[Matcher], message: str):
    async def _handle_cancel(text: Annotated[str, EventPlainText()]):
        if text == "取消":
            await matcher.finish(message)

    return Depends(_handle_cancel)


def do_add_sub(add_sub: Type[Matcher]):
    handle_cancel = gen_handle_cancel(add_sub, "已中止订阅")

    add_sub.handle()(ensure_user_info(add_sub))

    @add_sub.handle()
    async def init_promote(state: T_State):
        state["_prompt"] = (
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
        )

    @add_sub.got("platform", Message.template("{_prompt}"), [handle_cancel])
    async def parse_platform(state: T_State, platform: str = ArgPlainText()) -> None:
        if not isinstance(state["platform"], Message):
            return
        if platform == "全部":
            message = "全部平台\n" + "\n".join(
                [
                    "{}：{}".format(platform_name, platform.name)
                    for platform_name, platform in platform_manager.items()
                ]
            )
            await add_sub.reject(message)
        elif platform == "取消":
            await add_sub.finish("已中止订阅")
        elif platform in platform_manager:
            state["platform"] = platform
        else:
            await add_sub.reject("平台输入错误")

    @add_sub.handle()
    async def prepare_get_id(matcher: Matcher, state: T_State):
        cur_platform = platform_manager[state["platform"]]
        if cur_platform.has_target:
            state["_prompt"] = (
                ("1." + cur_platform.parse_target_promot + "\n2.")
                if cur_platform.parse_target_promot
                else ""
            ) + "请输入订阅用户的id\n查询id获取方法请回复:“查询”"
        else:
            matcher.set_arg("raw_id", Message("no id"))
            state["id"] = "default"
            state["name"] = await check_sub_target(state["platform"], Target(""))

    @add_sub.got("raw_id", Message.template("{_prompt}"), [handle_cancel])
    async def got_id(state: T_State, raw_id: str = ArgPlainText()):
        if state.get("id"):
            return
        try:
            if raw_id == "查询":
                url = "https://nonebot-bison.netlify.app/usage/#%E6%89%80%E6%94%AF%E6%8C%81%E5%B9%B3%E5%8F%B0%E7%9A%84-uid"
                title = "Bison所支持的平台UID"
                content = "查询相关平台的uid格式或获取方式"
                image = "https://s3.bmp.ovh/imgs/2022/03/ab3cc45d83bd3dd3.jpg"
                getId_share = f"[CQ:share,url={url},title={title},content={content},image={image}]"  # 缩短字符串格式长度，以及方便后续修改为消息段格式
                await add_sub.reject(Message(getId_share))
            platform = platform_manager[state["platform"]]
            raw_id = await platform.parse_target(unescape(raw_id))
            name = await check_sub_target(state["platform"], raw_id)
            if not name:
                await add_sub.reject("id输入错误")
            state["id"] = raw_id
            state["name"] = name
        except (Platform.ParseTargetException):
            await add_sub.reject("不能从你的输入中提取出id，请检查你输入的内容是否符合预期")
        else:
            await add_sub.send(
                "即将订阅的用户为:{} {} {}\n如有错误请输入“取消”重新订阅".format(
                    state["platform"], state["name"], state["id"]
                )
            )

    @add_sub.handle()
    async def prepare_get_categories(matcher: Matcher, state: T_State):
        if not platform_manager[state["platform"]].categories:
            matcher.set_arg("raw_cats", Message(""))
            state["cats"] = []
            return
        state["_prompt"] = "请输入要订阅的类别，以空格分隔，支持的类别有：{}".format(
            " ".join(list(platform_manager[state["platform"]].categories.values()))
        )

    @add_sub.got("raw_cats", Message.template("{_prompt}"), [handle_cancel])
    async def parser_cats(state: T_State, raw_cats: str = ArgPlainText()):
        if "cats" in state.keys():
            return
        res = []
        if platform_manager[state["platform"]].categories:
            for cat in raw_cats.split():
                if cat not in platform_manager[state["platform"]].reverse_category:
                    await add_sub.reject("不支持 {}".format(cat))
                res.append(platform_manager[state["platform"]].reverse_category[cat])
        state["cats"] = res

    @add_sub.handle()
    async def prepare_get_tags(matcher: Matcher, state: T_State):
        if not platform_manager[state["platform"]].enable_tag:
            matcher.set_arg("raw_tags", Message(""))
            state["tags"] = []
            return
        state["_prompt"] = '请输入要订阅/屏蔽的标签(不含#号)\n多个标签请使用空格隔开\n订阅所有标签输入"全部标签"\n具体规则回复"详情"'

    @add_sub.got("raw_tags", Message.template("{_prompt}"), [handle_cancel])
    async def parser_tags(state: T_State, raw_tags: str = ArgPlainText()):
        if "tags" in state.keys():
            return
        if raw_tags == "详情":
            await add_sub.reject(
                "订阅标签直接输入标签内容\n屏蔽标签请在标签名称前添加~号\n详见https://nonebot-bison.netlify.app/usage/#%E5%B9%B3%E5%8F%B0%E8%AE%A2%E9%98%85%E6%A0%87%E7%AD%BE-tag"
            )
        if raw_tags in ["全部标签", "全部", "全标签"]:
            state["tags"] = []
        else:
            state["tags"] = raw_tags.split()

    @add_sub.handle()
    async def add_sub_process(state: T_State):
        user = cast(PlatformTarget, state.get("target_user_info"))
        assert isinstance(user, PlatformTarget)
        try:
            await config.add_subscribe(
                user=user,
                target=state["id"],
                target_name=state["name"],
                platform_name=state["platform"],
                cats=state.get("cats", []),
                tags=state.get("tags", []),
            )
        except SubscribeDupException:
            await add_sub.finish(f"添加 {state['name']} 失败: 已存在该订阅")
        except Exception as e:
            await add_sub.finish(f"添加 {state['name']} 失败: {e}")
        await add_sub.finish("添加 {} 成功".format(state["name"]))


def do_query_sub(query_sub: Type[Matcher]):
    query_sub.handle()(ensure_user_info(query_sub))

    @query_sub.handle()
    async def _(bot: Bot, state: T_State):
        user_info = state["target_user_info"]
        assert isinstance(user_info, PlatformTarget)
        sub_list = await config.list_subscribe(user_info)
        res = "订阅的帐号为：\n"
        for sub in sub_list:
            res += "{} {} {}".format(
                # sub["target_type"], sub["target_name"], sub["target"]
                sub.target.platform_name,
                sub.target.target_name,
                sub.target.target,
            )
            platform = platform_manager[sub.target.platform_name]
            if platform.categories:
                res += " [{}]".format(
                    ", ".join(
                        map(lambda x: platform.categories[Category(x)], sub.categories)
                    )
                )
            if platform.enable_tag:
                res += " {}".format(", ".join(sub.tags))
            res += "\n"
        await MessageFactory(await parse_text(res)).send()
        await query_sub.finish()


def do_del_sub(del_sub: Type[Matcher]):
    handle_cancel = gen_handle_cancel(del_sub, "删除中止")

    del_sub.handle()(ensure_user_info(del_sub))

    @del_sub.handle()
    async def send_list(bot: Bot, event: Event, state: T_State):
        user_info = state["target_user_info"]
        assert isinstance(user_info, PlatformTarget)
        try:
            sub_list = await config.list_subscribe(user_info)
            assert sub_list
        except AssertionError:
            await del_sub.finish("暂无已订阅账号\n请使用“添加订阅”命令添加订阅")
        else:
            res = "订阅的帐号为：\n"
            state["sub_table"] = {}
            for index, sub in enumerate(sub_list, 1):
                state["sub_table"][index] = {
                    "platform_name": sub.target.platform_name,
                    "target": sub.target.target,
                }
                res += "{} {} {} {}\n".format(
                    index,
                    sub.target.platform_name,
                    sub.target.target_name,
                    sub.target.target,
                )
                platform = platform_manager[sub.target.platform_name]
                if platform.categories:
                    res += " [{}]".format(
                        ", ".join(
                            map(
                                lambda x: platform.categories[Category(x)],
                                sub.categories,
                            )
                        )
                    )
                if platform.enable_tag:
                    res += " {}".format(", ".join(sub.tags))
                res += "\n"
            res += "请输入要删除的订阅的序号\n输入'取消'中止"
            await MessageFactory(await parse_text(res)).send()

    @del_sub.receive(parameterless=[handle_cancel])
    async def do_del(state: T_State, index_str: str = EventPlainText()):
        try:
            index = int(index_str)
            user_info = state["target_user_info"]
            assert isinstance(user_info, PlatformTarget)
            await config.del_subscribe(user_info, **state["sub_table"][index])
        except Exception as e:
            await del_sub.reject("删除错误")
        else:
            await del_sub.finish("删除成功")


add_sub_matcher = on_command(
    "添加订阅",
    rule=configurable_to_me,
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=5,
    block=True,
)
add_sub_matcher.handle()(set_target_user_info)
do_add_sub(add_sub_matcher)


query_sub_matcher = on_command("查询订阅", rule=configurable_to_me, priority=5, block=True)
query_sub_matcher.handle()(set_target_user_info)
do_query_sub(query_sub_matcher)


del_sub_matcher = on_command(
    "删除订阅",
    rule=configurable_to_me,
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=5,
    block=True,
)
del_sub_matcher.handle()(set_target_user_info)
do_del_sub(del_sub_matcher)

group_manage_matcher = on_command(
    "群管理", rule=to_me(), permission=SUPERUSER, priority=4, block=True
)

group_handle_cancel = gen_handle_cancel(group_manage_matcher, "已取消")


@group_manage_matcher.handle()
async def send_group_list_private(bot: Bot, event: GroupMessageEvent, state: T_State):
    await group_manage_matcher.finish(Message("该功能只支持私聊使用，请私聊Bot"))


@group_manage_matcher.handle()
async def send_group_list(bot: Bot, event: PrivateMessageEvent, state: T_State):
    groups = await bot.call_api("get_group_list")
    res_text = "请选择需要管理的群：\n"
    group_number_idx = {}
    for idx, group in enumerate(groups, 1):
        group_number_idx[idx] = group["group_id"]
        res_text += f'{idx}. {group["group_id"]} - {group["group_name"]}\n'
    res_text += "请输入左侧序号\n中止操作请输入'取消'"
    # await group_manage_matcher.send(res_text)
    state["_prompt"] = res_text
    state["group_number_idx"] = group_number_idx


@group_manage_matcher.got(
    "group_idx", Message.template("{_prompt}"), [group_handle_cancel]
)
async def do_choose_group_number(state: T_State, group_idx: str = ArgPlainText()):
    group_number_idx: dict[int, int] = state["group_number_idx"]
    assert group_number_idx
    idx = int(group_idx)
    if idx not in group_number_idx.keys():
        await group_manage_matcher.reject("请输入正确序号")
    state["group_idx"] = idx
    group_number_idx: dict[int, int] = state["group_number_idx"]
    idx: int = state["group_idx"]
    group_id = group_number_idx[idx]
    state["target_user_info"] = TargetQQGroup(group_id=group_id)


@group_manage_matcher.got(
    "command", "请输入需要使用的命令：添加订阅，查询订阅，删除订阅，取消", [group_handle_cancel]
)
async def do_dispatch_command(
    bot: Bot,
    event: MessageEvent,
    state: T_State,
    matcher: Matcher,
    command: str = ArgStr(),
):
    if command not in {"添加订阅", "查询订阅", "删除订阅", "取消"}:
        await group_manage_matcher.reject("请输入正确的命令")
    permission = await matcher.update_permission(bot, event)
    new_matcher = Matcher.new(
        "message",
        Rule(),
        permission,
        handlers=None,
        temp=True,
        priority=0,
        block=True,
        plugin=matcher.plugin,
        module=matcher.module,
        expire_time=datetime.now(),
        default_state=matcher.state,
        default_type_updater=matcher.__class__._default_type_updater,
        default_permission_updater=matcher.__class__._default_permission_updater,
    )
    if command == "查询订阅":
        do_query_sub(new_matcher)
    elif command == "添加订阅":
        do_add_sub(new_matcher)
    else:
        do_del_sub(new_matcher)
    new_matcher_ins = new_matcher()
    asyncio.create_task(new_matcher_ins.run(bot, event, state))
