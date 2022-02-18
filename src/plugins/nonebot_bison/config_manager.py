from typing import Type

from nonebot import on_command
from nonebot.adapters import Event as AbstractEvent
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.internal.rule import Rule
from nonebot.matcher import Matcher
from nonebot.params import Depends, EventToMe
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State

from .config import Config
from .platform import check_sub_target, platform_manager
from .plugin_config import plugin_config
from .types import Category, Target
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


def do_add_sub(add_sub: Type[Matcher]):
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
            + "要查看全部平台请输入：“全部”"
        )

    async def parse_platform(event: AbstractEvent, state: T_State) -> None:
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
        elif platform in platform_manager:
            state["platform"] = platform
        else:
            await add_sub.reject("平台输入错误")

    @add_sub.got(
        "platform", _gen_prompt_template("{_prompt}"), [Depends(parse_platform)]
    )
    async def init_id(state: T_State):
        if platform_manager[state["platform"]].has_target:
            state[
                "_prompt"
            ] = "请输入订阅用户的id，详情查阅https://nonebot-bison.vercel.app/usage/#%E6%89%80%E6%94%AF%E6%8C%81%E5%B9%B3%E5%8F%B0%E7%9A%84uid"
        else:
            state["id"] = "default"
            state["name"] = await platform_manager[state["platform"]].get_target_name(
                Target("")
            )

    async def parse_id(event: AbstractEvent, state: T_State):
        if not isinstance(state["id"], Message):
            return
        target = str(event.get_message()).strip()
        try:
            name = await check_sub_target(state["platform"], target)
            if not name:
                raise ValueError
            state["id"] = target
            state["name"] = name
        except:
            await add_sub.reject("id输入错误")

    @add_sub.got("id", _gen_prompt_template("{_prompt}"), [Depends(parse_id)])
    async def init_cat(state: T_State):
        if not platform_manager[state["platform"]].categories:
            state["cats"] = []
            return
        state["_prompt"] = "请输入要订阅的类别，以空格分隔，支持的类别有：{}".format(
            " ".join(list(platform_manager[state["platform"]].categories.values()))
        )

    async def parser_cats(event: AbstractEvent, state: T_State):
        if not isinstance(state["cats"], Message):
            return
        res = []
        for cat in str(event.get_message()).strip().split():
            if cat not in platform_manager[state["platform"]].reverse_category:
                await add_sub.reject("不支持 {}".format(cat))
            res.append(platform_manager[state["platform"]].reverse_category[cat])
        state["cats"] = res

    @add_sub.got("cats", _gen_prompt_template("{_prompt}"), [Depends(parser_cats)])
    async def init_tag(state: T_State):
        if not platform_manager[state["platform"]].enable_tag:
            state["tags"] = []
            return
        state["_prompt"] = '请输入要订阅的tag，订阅所有tag输入"全部标签"'

    async def parser_tags(event: AbstractEvent, state: T_State):
        if not isinstance(state["tags"], Message):
            return
        if str(event.get_message()).strip() == "全部标签":
            state["tags"] = []
        else:
            state["tags"] = str(event.get_message()).strip().split()

    @add_sub.got("tags", _gen_prompt_template("{_prompt}"), [Depends(parser_tags)])
    async def add_sub_process(event: Event, state: T_State):
        config = Config()
        config.add_subscribe(
            state.get("_user_id") or event.group_id,
            user_type="group",
            target=state["id"],
            target_name=state["name"],
            target_type=state["platform"],
            cats=state.get("cats", []),
            tags=state.get("tags", []),
        )
        await add_sub.finish("添加 {} 成功".format(state["name"]))


def do_query_sub(query_sub: Type[Matcher]):
    @query_sub.handle()
    async def _(event: Event, state: T_State):
        config: Config = Config()
        sub_list = config.list_subscribe(
            state.get("_user_id") or event.group_id, "group"
        )
        res = "订阅的帐号为：\n"
        for sub in sub_list:
            res += "{} {} {}".format(
                sub["target_type"], sub["target_name"], sub["target"]
            )
            platform = platform_manager[sub["target_type"]]
            if platform.categories:
                res += " [{}]".format(
                    ", ".join(
                        map(lambda x: platform.categories[Category(x)], sub["cats"])
                    )
                )
            if platform.enable_tag:
                res += " {}".format(", ".join(sub["tags"]))
            res += "\n"
        await query_sub.finish(Message(await parse_text(res)))


def do_del_sub(del_sub: Type[Matcher]):
    @del_sub.handle()
    async def send_list(bot: Bot, event: Event, state: T_State):
        config: Config = Config()
        sub_list = config.list_subscribe(
            state.get("_user_id") or event.group_id, "group"
        )
        res = "订阅的帐号为：\n"
        state["sub_table"] = {}
        for index, sub in enumerate(sub_list, 1):
            state["sub_table"][index] = {
                "target_type": sub["target_type"],
                "target": sub["target"],
            }
            res += "{} {} {} {}\n".format(
                index, sub["target_type"], sub["target_name"], sub["target"]
            )
            platform = platform_manager[sub["target_type"]]
            if platform.categories:
                res += " [{}]".format(
                    ", ".join(
                        map(lambda x: platform.categories[Category(x)], sub["cats"])
                    )
                )
            if platform.enable_tag:
                res += " {}".format(", ".join(sub["tags"]))
            res += "\n"
        res += "请输入要删除的订阅的序号"
        await bot.send(event=event, message=Message(await parse_text(res)))

    @del_sub.receive()
    async def do_del(event: Event, state: T_State):
        try:
            index = int(str(event.get_message()).strip())
            config = Config()
            config.del_subscribe(
                state.get("_user_id") or event.group_id,
                "group",
                **state["sub_table"][index],
            )
        except Exception as e:
            await del_sub.reject("删除错误")
        else:
            await del_sub.finish("删除成功")


async def parse_group_number(event: AbstractEvent, state: T_State):
    if not isinstance(state["_user_id"], Message):
        return
    state["_user_id"] = int(str(event.get_message()))


add_sub_matcher = on_command(
    "添加订阅",
    rule=configurable_to_me,
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=5,
)
do_add_sub(add_sub_matcher)
manage_add_sub_matcher = on_command("管理-添加订阅", permission=SUPERUSER, priority=5)


@manage_add_sub_matcher.got("_user_id", "群号", [Depends(parse_group_number)])
async def add_sub_handle():
    pass


do_add_sub(manage_add_sub_matcher)


query_sub_matcher = on_command("查询订阅", rule=configurable_to_me, priority=5)
do_query_sub(query_sub_matcher)
manage_query_sub_matcher = on_command("管理-查询订阅", permission=SUPERUSER, priority=5)


@manage_query_sub_matcher.got("_user_id", "群号", [Depends(parse_group_number)])
async def query_sub_handle():
    pass


do_query_sub(manage_query_sub_matcher)


del_sub_matcher = on_command(
    "删除订阅",
    rule=configurable_to_me,
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
    priority=5,
)
do_del_sub(del_sub_matcher)
manage_del_sub_matcher = on_command("管理-删除订阅", permission=SUPERUSER, priority=5)


@manage_del_sub_matcher.got("_user_id", "群号", [Depends(parse_group_number)])
async def del_sub_handle():
    pass


do_del_sub(manage_del_sub_matcher)
