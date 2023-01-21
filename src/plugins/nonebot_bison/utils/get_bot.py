""" 提供获取 Bot 的方法 """
import random
from typing import Optional

from nonebot import get_bots, get_driver, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    FriendAddNoticeEvent,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
)

from ..types import User

GROUP: dict[int, list[Bot]] = {}
USER: dict[int, list[Bot]] = {}

driver = get_driver()


@driver.on_bot_connect
async def _on_bot_connect(bot: Bot):
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


@driver.on_bot_disconnect
async def _on_bot_disconnect(bot: Bot):
    for bots in GROUP.values():
        if bot in bots:
            bots.remove(bot)

    for bots in USER.values():
        if bot in bots:
            bots.remove(bot)


change_notice = on_notice(priority=1)


@change_notice.handle()
async def _friend_add(bot: Bot, event: FriendAddNoticeEvent):
    user_id = event.user_id
    if user_id not in USER:
        USER[user_id] = [bot]
    else:
        USER[user_id].append(bot)


# 01-06 16:56:51 [SUCCESS] nonebot | OneBot V11 **** | [notice.group_increase.approve]: {'time': 1672995411, 'self_id': ****, 'post_type': 'notice', 'notice_type': 'group_increase', 'sub_type': 'approve', 'user_id': ****, 'group_id': ****, 'operator_id': 0}
@change_notice.handle()
async def _group_increase(bot: Bot, event: GroupIncreaseNoticeEvent):
    if bot.self_id == event.user_id:
        group_id = event.group_id
        if group_id not in GROUP:
            GROUP[group_id] = [bot]
        else:
            GROUP[group_id].append(bot)


# 01-06 16:58:09 [SUCCESS] nonebot | OneBot V11 **** | [notice.group_decrease.kick_me]: {'time': 1672995489, 'self_id': ****, 'post_type': 'notice', 'notice_type': 'group_decrease', 'sub_type': 'kick_me', 'user_id': ****, 'group_id': ****, 'operator_id': ****}
@change_notice.handle()
async def _group_decrease(bot: Bot, event: GroupDecreaseNoticeEvent):
    if bot.self_id == event.user_id:
        group_id = event.group_id
        if group_id in GROUP and bot in GROUP[group_id]:
            GROUP[group_id].remove(bot)


async def refresh_bots():
    """刷新 Bot"""
    GROUP.clear()
    USER.clear()
    for bot in get_bots():
        if isinstance(bot, Bot):
            await _on_bot_connect(bot)


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
