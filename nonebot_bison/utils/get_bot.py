"""提供获取 Bot 的方法"""

from typing import Any
from collections import defaultdict

import nonebot
from nonebot.adapters import Bot
from nonebot_plugin_saa import PlatformTarget
from nonebot.adapters.onebot.v11 import Bot as Ob11Bot

GROUP: dict[int, list[Bot]] = {}
USER: dict[int, list[Bot]] = {}
BOT_CACHE: dict[PlatformTarget, list[Bot]] = defaultdict(list)


def get_bots() -> list[Bot]:
    """获取所有 OneBot 11 Bot"""
    # TODO: support ob12
    bots = []
    for bot in nonebot.get_bots().values():
        if isinstance(bot, Ob11Bot):
            bots.append(bot)
    return bots


async def get_groups() -> list[dict[str, Any]]:
    """获取所有群号"""
    # TODO
    all_groups: dict[int, dict[str, Any]] = {}
    for bot in get_bots():
        groups = await bot.get_group_list()
        all_groups.update({group["group_id"]: group for group in groups if group["group_id"] not in all_groups})

    return list(all_groups.values())
