from typing import Type

from nonebot.matcher import Matcher
from nonebot.params import Arg
from nonebot_plugin_saa import MessageFactory, PlatformTarget

from ..config import config
from ..platform import platform_manager
from ..types import Category
from ..utils import parse_text
from .utils import ensure_user_info


def do_query_sub(query_sub: Type[Matcher]):
    query_sub.handle()(ensure_user_info(query_sub))

    @query_sub.handle()
    async def _(user_info: PlatformTarget = Arg("target_user_info")):
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
