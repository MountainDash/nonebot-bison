""" 提供获取 Bot 的方法 """
from nonebot import get_driver, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    FriendAddNoticeEvent,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
)

GROUP: dict[str, set[Bot]] = {}
USER: dict[str, set[Bot]] = {}

driver = get_driver()


@driver.on_bot_connect
async def _(bot: Bot):
    # 获取群列表
    groups = await bot.get_group_list()
    for group in groups:
        group_id = group["group_id"]
        if group_id not in GROUP:
            GROUP[group_id] = {bot}
        else:
            GROUP[group_id].add(bot)

    # 获取好友列表
    users = await bot.get_friend_list()
    for user in users:
        user_id = user["user_id"]
        if user_id not in USER:
            USER[user_id] = {bot}
        else:
            USER[user_id].add(bot)


@driver.on_bot_disconnect
async def _(bot: Bot):
    for bots in GROUP.values():
        if bot in bots:
            bots.remove(bot)

    for bots in USER.values():
        if bot in bots:
            bots.remove(bot)


change_notice = on_notice(priority=1)


@change_notice.handle()
async def _(bot: Bot, event: FriendAddNoticeEvent):
    user_id = str(event.user_id)
    if user_id not in USER:
        USER[user_id] = {bot}
    else:
        USER[user_id].add(bot)


# 01-06 16:56:51 [SUCCESS] nonebot | OneBot V11 **** | [notice.group_increase.approve]: {'time': 1672995411, 'self_id': ****, 'post_type': 'notice', 'notice_type': 'group_increase', 'sub_type': 'approve', 'user_id': ****, 'group_id': ****, 'operator_id': 0}
@change_notice.handle()
async def _(bot: Bot, event: GroupIncreaseNoticeEvent):
    if bot.self_id == event.user_id:
        group_id = str(event.group_id)
        if group_id not in GROUP:
            GROUP[group_id] = {bot}
        else:
            GROUP[group_id].add(bot)


# 01-06 16:58:09 [SUCCESS] nonebot | OneBot V11 **** | [notice.group_decrease.kick_me]: {'time': 1672995489, 'self_id': ****, 'post_type': 'notice', 'notice_type': 'group_decrease', 'sub_type': 'kick_me', 'user_id': ****, 'group_id': ****, 'operator_id': ****}
@change_notice.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent):
    if bot.self_id == event.user_id:
        group_id = str(event.group_id)
        if group_id in GROUP and bot in GROUP[group_id]:
            GROUP[group_id].remove(bot)
