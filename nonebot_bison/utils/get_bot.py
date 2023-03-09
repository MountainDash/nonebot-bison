""" 提供获取 Bot 的方法 """
import random
from typing import Any, Optional

import nonebot
from nonebot import get_driver, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    FriendAddNoticeEvent,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
)

from ..types import User

GROUP: dict[int, list[Bot]] = {}
USER: dict[int, list[Bot]] = {}


def get_bots() -> list[Bot]:
    """获取所有 OneBot 11 Bot"""
    bots = []
    for bot in nonebot.get_bots().values():
        if isinstance(bot, Bot):
            bots.append(bot)
    return bots


async def refresh_bots():
    """刷新缓存的 Bot 数据"""
    GROUP.clear()
    USER.clear()
    for bot in get_bots():
        # 获取群列表
        groups = await bot.get_group_list()
        for group in groups:
            group_id = group["group_id"]
            if group_id not in GROUP:
                GROUP[group_id] = [bot]
            else:
                GROUP[group_id].append(bot)

        # 获取好友列表
        users = await bot.get_friend_list()
        for user in users:
            user_id = user["user_id"]
            if user_id not in USER:
                USER[user_id] = [bot]
            else:
                USER[user_id].append(bot)


driver = get_driver()


@driver.on_bot_connect
@driver.on_bot_disconnect
async def _(bot: Bot):
    await refresh_bots()


change_notice = on_notice(priority=1)


@change_notice.handle()
async def _(bot: Bot, event: FriendAddNoticeEvent):
    await refresh_bots()


# 01-06 16:56:51 [SUCCESS] nonebot | OneBot V11 **** | [notice.group_increase.approve]: {'time': 1672995411, 'self_id': ****, 'post_type': 'notice', 'notice_type': 'group_increase', 'sub_type': 'approve', 'user_id': ****, 'group_id': ****, 'operator_id': 0}
# 01-06 16:58:09 [SUCCESS] nonebot | OneBot V11 **** | [notice.group_decrease.kick_me]: {'time': 1672995489, 'self_id': ****, 'post_type': 'notice', 'notice_type': 'group_decrease', 'sub_type': 'kick_me', 'user_id': ****, 'group_id': ****, 'operator_id': ****}
@change_notice.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent | GroupIncreaseNoticeEvent):
    if bot.self_id == event.user_id:
        await refresh_bots()


def get_bot(user: User) -> Optional[Bot]:
    """获取 Bot"""
    bots = []
    if user.user_type == "group":
        bots = GROUP.get(user.user, [])

    if user.user_type == "private":
        bots = USER.get(user.user, [])

    if not bots:
        return

    return random.choice(bots)


async def get_groups() -> list[dict[str, Any]]:
    """获取所有群号"""
    all_groups: dict[int, dict[str, Any]] = {}
    for bot in get_bots():
        groups = await bot.get_group_list()
        all_groups.update(
            {
                group["group_id"]: group
                for group in groups
                if group["group_id"] not in all_groups
            }
        )

    return list(all_groups.values())
