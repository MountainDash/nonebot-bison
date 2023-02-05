import asyncio
from asyncio.tasks import sleep
from collections import deque
from typing import Deque, Literal, Union

from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.log import logger

from .plugin_config import plugin_config
from .utils.get_bot import refresh_bots

QUEUE: Deque[
    tuple[
        Bot,
        int,
        Literal["private", "group", "group-forward"],
        Union[str, Message],
        int,
    ]
] = deque()

MESSGE_SEND_INTERVAL = 1.5


async def _do_send(
    bot: "Bot",
    user: int,
    user_type: Literal["group", "private", "group-forward"],
    msg: Union[str, Message],
):
    try:
        if user_type == "group":
            await bot.send_group_msg(group_id=user, message=msg)
        elif user_type == "private":
            await bot.send_private_msg(user_id=user, message=msg)
        elif user_type == "group-forward":
            await bot.send_group_forward_msg(group_id=user, messages=msg)
    except ActionFailed:
        await refresh_bots()
        logger.warning(f"send msg failed, refresh bots")


async def do_send_msgs():
    if not QUEUE:
        return
    while True:
        # why read from queue then pop item from queue?
        # if there is only 1 item in queue, pop it and await send
        # the length of queue will be 0.
        # At that time, adding items to queue will trigger a new execution of this func, which is wrong.
        # So, read from queue first then pop from it
        bot, user, user_type, msg, retry_time = QUEUE[0]
        try:
            await _do_send(bot, user, user_type, msg)
        except Exception as e:
            await asyncio.sleep(MESSGE_SEND_INTERVAL)
            QUEUE.popleft()
            if retry_time > 0:
                QUEUE.appendleft((bot, user, user_type, msg, retry_time - 1))
            else:
                msg_str = str(msg)
                if len(msg_str) > 50:
                    msg_str = msg_str[:50] + "..."
                logger.warning(f"send msg err {e} {msg_str}")
        else:
            # sleeping after popping may also cause re-execution error like above mentioned
            await asyncio.sleep(MESSGE_SEND_INTERVAL)
            QUEUE.popleft()
        finally:
            if not QUEUE:
                return


async def _send_msgs_dispatch(
    bot: Bot,
    user,
    user_type: Literal["private", "group", "group-forward"],
    msg: Union[str, Message],
):
    if plugin_config.bison_use_queue:
        QUEUE.append((bot, user, user_type, msg, plugin_config.bison_resend_times))
        # len(QUEUE) before append was 0
        if len(QUEUE) == 1:
            asyncio.create_task(do_send_msgs())
    else:
        await _do_send(bot, user, user_type, msg)


async def send_msgs(
    bot: Bot, user, user_type: Literal["private", "group"], msgs: list[Message]
):
    if not plugin_config.bison_use_pic_merge or user_type == "private":
        for msg in msgs:
            await _send_msgs_dispatch(bot, user, user_type, msg)
        return
    msgs = msgs.copy()
    if plugin_config.bison_use_pic_merge == 1:
        await _send_msgs_dispatch(bot, user, "group", msgs.pop(0))
    if msgs:
        if len(msgs) == 1:  # 只有一条消息序列就不合并转发
            await _send_msgs_dispatch(bot, user, "group", msgs.pop(0))
        else:
            group_bot_info = await bot.get_group_member_info(
                group_id=user, user_id=int(bot.self_id), no_cache=True
            )  # 调用api获取群内bot的相关参数
            forward_msg = Message(
                [
                    MessageSegment.node_custom(
                        group_bot_info["user_id"],
                        nickname=group_bot_info["card"] or group_bot_info["nickname"],
                        content=msg,
                    )
                    for msg in msgs
                ]
            )

            await _send_msgs_dispatch(bot, user, "group-forward", forward_msg)
