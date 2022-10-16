import asyncio
from datetime import datetime
from typing import Optional, Type, cast

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, MessageEvent
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.internal.params import ArgStr
from nonebot.internal.rule import Rule
from nonebot.matcher import Matcher
from nonebot.params import Depends, EventPlainText, EventToMe
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State

from .apis import check_sub_target
from .config import config
from .config.db_config import SubscribeDupException
from .platform import Platform, platform_manager
from .plugin_config import plugin_config
from .types import Category, Target, User
from .utils import parse_text


def _gen_prompt_template(prompt: str):
    if hasattr(Message, "template"):
        return Message.template(prompt)
    return prompt


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


async def set_target_user_info(event: MessageEvent, state: T_State):
    if isinstance(event, GroupMessageEvent):
        user = User(event.group_id, "group")
        state["target_user_info"] = user
    elif isinstance(event, PrivateMessageEvent):
        user = User(event.user_id, "private")
        state["target_user_info"] = user


def do_add_sub(add_sub: Type[Matcher]):
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

    async def parse_platform(event: MessageEvent, state: T_State) -> None:
        if not isinstance(state["platform"], Message):
            return
        platform = str(event.get_message()).strip()
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

    @add_sub.got(
        "platform", _gen_prompt_template("{_prompt}"), [Depends(parse_platform)]
    )
    async def init_id(state: T_State):
        cur_platform = platform_manager[state["platform"]]
        if cur_platform.has_target:
            state["_prompt"] = (
                ("1." + cur_platform.parse_target_promot + "\n2.")
                if cur_platform.parse_target_promot
                else ""
            ) + "请输入订阅用户的id\n查询id获取方法请回复:“查询”"
        else:
            state["id"] = "default"
            state["name"] = await check_sub_target(state["platform"], Target(""))

    async def parse_id(event: MessageEvent, state: T_State):
        if not isinstance(state["id"], Message):
            return
        target = str(event.get_message()).strip()
        try:
            if target == "查询":
                raise LookupError
            if target == "取消":
                raise KeyboardInterrupt
            platform = platform_manager[state["platform"]]
            target = await platform.parse_target(target)
            name = await check_sub_target(state["platform"], target)
            if not name:
                raise ValueError
            state["id"] = target
            state["name"] = name
        except (LookupError):
            url = "https://nonebot-bison.netlify.app/usage/#%E6%89%80%E6%94%AF%E6%8C%81%E5%B9%B3%E5%8F%B0%E7%9A%84-uid"
            title = "Bison所支持的平台UID"
            content = "查询相关平台的uid格式或获取方式"
            image = "https://s3.bmp.ovh/imgs/2022/03/ab3cc45d83bd3dd3.jpg"
            getId_share = f"[CQ:share,url={url},title={title},content={content},image={image}]"  # 缩短字符串格式长度，以及方便后续修改为消息段格式
            await add_sub.reject(Message(getId_share))
        except (KeyboardInterrupt):
            await add_sub.finish("已中止订阅")
        except (ValueError):
            await add_sub.reject("id输入错误")
        except (Platform.ParseTargetException):
            await add_sub.reject("不能从你的输入中提取出id，请检查你输入的内容是否符合预期")
        else:
            await add_sub.send(
                "即将订阅的用户为:{} {} {}\n如有错误请输入“取消”重新订阅".format(
                    state["platform"], state["name"], state["id"]
                )
            )

    @add_sub.got("id", _gen_prompt_template("{_prompt}"), [Depends(parse_id)])
    async def init_cat(state: T_State):
        if not platform_manager[state["platform"]].categories:
            state["cats"] = []
            return
        state["_prompt"] = "请输入要订阅的类别，以空格分隔，支持的类别有：{}".format(
            " ".join(list(platform_manager[state["platform"]].categories.values()))
        )

    async def parser_cats(event: MessageEvent, state: T_State):
        if not isinstance(state["cats"], Message):
            return
        res = []
        for cat in str(event.get_message()).strip().split():
            if cat == "取消":
                await add_sub.finish("已中止订阅")
            elif cat not in platform_manager[state["platform"]].reverse_category:
                await add_sub.reject("不支持 {}".format(cat))
            res.append(platform_manager[state["platform"]].reverse_category[cat])
        state["cats"] = res

    @add_sub.got("cats", _gen_prompt_template("{_prompt}"), [Depends(parser_cats)])
    async def init_tag(state: T_State):
        if not platform_manager[state["platform"]].enable_tag:
            state["tags"] = []
            return
        state["_prompt"] = '请输入要订阅/屏蔽的tag(不含#号)\n多个tag请使用空格隔开\n具体规则回复"详情"'

    async def parser_tags(event: MessageEvent, state: T_State):
        if not isinstance(state["tags"], Message):
            return
        if str(event.get_message()).strip() == "取消":  # 一般不会有叫 取消 的tag吧
            await add_sub.finish("已中止订阅")
        if str(event.get_message()).strip() == "详情":
            await add_sub.reject(
                '订阅tag直接输入tag内容\n订阅所有tag输入"全部标签"\n屏蔽tag请在tag名称前添加~号\n详见https://nonebot-bison.netlify.app/usage/#平台订阅标签-tag'
            )
        if str(event.get_message()).strip() == "全部标签":
            state["tags"] = []
        else:
            state["tags"] = str(event.get_message()).strip().split()

    @add_sub.got("tags", _gen_prompt_template("{_prompt}"), [Depends(parser_tags)])
    async def add_sub_process(event: Event, state: T_State):
        user = cast(User, state.get("target_user_info"))
        assert isinstance(user, User)
        try:
            await config.add_subscribe(
                # state.get("_user_id") or event.group_id,
                # user_type="group",
                user=user.user,
                user_type=user.user_type,
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
    async def _(state: T_State):
        user_info = state["target_user_info"]
        assert isinstance(user_info, User)
        sub_list = await config.list_subscribe(
            # state.get("_user_id") or event.group_id, "group"
            user_info.user,
            user_info.user_type,
        )
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
        await query_sub.finish(Message(await parse_text(res)))


def do_del_sub(del_sub: Type[Matcher]):
    del_sub.handle()(ensure_user_info(del_sub))

    @del_sub.handle()
    async def send_list(bot: Bot, event: Event, state: T_State):
        user_info = state["target_user_info"]
        assert isinstance(user_info, User)
        try:
            sub_list = await config.list_subscribe(
                # state.get("_user_id") or event.group_id, "group"
                user_info.user,
                user_info.user_type,
            )
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
            await bot.send(event=event, message=Message(await parse_text(res)))

    @del_sub.receive()
    async def do_del(event: Event, state: T_State):
        user_msg = str(event.get_message()).strip()
        if user_msg == "取消":
            await del_sub.finish("删除中止")
        try:
            index = int(user_msg)
            user_info = state["target_user_info"]
            assert isinstance(user_info, User)
            await config.del_subscribe(
                # state.get("_user_id") or event.group_id,
                # "group",
                user_info.user,
                user_info.user_type,
                **state["sub_table"][index],
            )
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


async def _parse_group_idx(state: T_State, event_msg: str = EventPlainText()):
    if not isinstance(state["group_idx"], Message):
        return
    group_number_idx: Optional[dict[int, int]] = state.get("group_number_idx")
    assert group_number_idx
    try:
        assert event_msg != "取消", "userAbort"
        idx = int(event_msg)
        assert idx in group_number_idx.keys(), "idxNotInList"
        state["group_idx"] = idx
    except AssertionError as AE:
        errType = AE.args[0]
        if errType == "userAbort":
            await group_manage_matcher.finish("已取消")
        elif errType == "idxNotInList":
            await group_manage_matcher.reject("请输入正确序号")


@group_manage_matcher.got(
    "group_idx", _gen_prompt_template("{_prompt}"), [Depends(_parse_group_idx)]
)
async def do_choose_group_number(state: T_State):
    group_number_idx: dict[int, int] = state["group_number_idx"]
    idx: int = state["group_idx"]
    group_id = group_number_idx[idx]
    state["target_user_info"] = User(user=group_id, user_type="group")


async def _check_command(event_msg: str = EventPlainText()):
    if event_msg not in {"添加订阅", "查询订阅", "删除订阅", "取消"}:
        await group_manage_matcher.reject("请输入正确的命令")
    return


@group_manage_matcher.got(
    "command", "请输入需要使用的命令：添加订阅，查询订阅，删除订阅，取消", [Depends(_check_command)]
)
async def do_dispatch_command(
    bot: Bot,
    event: MessageEvent,
    state: T_State,
    matcher: Matcher,
    command: str = ArgStr(),
):
    if command == "取消":
        await group_manage_matcher.finish("已取消")
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
