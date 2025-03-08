from nonebot.matcher import Matcher
from nonebot.params import Arg
from nonebot_plugin_saa import MessageFactory, PlatformTarget

from nonebot_bison.config import config
from nonebot_bison.platform import platform_manager
from nonebot_bison.types import Category
from nonebot_bison.utils import parse_text

from .utils import ensure_user_info


def do_query_sub(query_sub: type[Matcher]):
    query_sub.handle()(ensure_user_info(query_sub))

    @query_sub.handle()
    async def _(user_info: PlatformTarget = Arg("target_user_info")):
        sub_list = await config.list_subscribe(user_info)
        res = "订阅的帐号为：\n"
        for sub in sub_list:
            res += f"{sub.target.platform_name} {sub.target.target_name} {sub.target.target}\n"
            if platform := platform_manager.get(sub.target.platform_name):
                if platform.categories:
                    res += " [{}]".format(", ".join(platform.categories[Category(x)] for x in sub.categories))
                if platform.enable_tag:
                    res += " {}".format(", ".join(sub.tags))
            else:
                res += f" （平台 {sub.target.platform_name} 已失效，请删除此订阅）"
            if res[-1] != "\n":
                res += "\n"
        await MessageFactory(await parse_text(res)).send()
        await query_sub.finish()
