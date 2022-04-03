import time
from typing import Literal, Union

from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.log import logger

from .plugin_config import plugin_config

QUEUE: list[
    tuple[
        Bot,
        int,
        Literal["private", "group", "group-forward"],
        Union[str, Message],
        int,
    ]
] = []
LAST_SEND_TIME = time.time()


async def _do_send(
    bot: "Bot",
    user: int,
    user_type: Literal["group", "private", "group-forward"],
    msg: Union[str, Message],
):
    if user_type == "group":
        await bot.send_group_msg(group_id=user, message=msg)
    elif user_type == "private":
        await bot.send_private_msg(user_id=user, message=msg)
    elif user_type == "group-forward":
        await bot.send_group_forward_msg(group_id=user, messages=msg)


async def do_send_msgs():
    global LAST_SEND_TIME
    if time.time() - LAST_SEND_TIME < 1.5:
        return
    if QUEUE:
        bot, user, user_type, msg, retry_time = QUEUE.pop(0)
        try:
            await _do_send(bot, user, user_type, msg)
        except Exception as e:
            if retry_time > 0:
                QUEUE.insert(0, (bot, user, user_type, msg, retry_time - 1))
            else:
                msg_str = str(msg)
                if len(msg_str) > 50:
                    msg_str = msg_str[:50] + "..."
                logger.warning(f"send msg err {e} {msg_str}")
        LAST_SEND_TIME = time.time()


async def _send_msgs_dispatch(
    bot: Bot,
    user,
    user_type: Literal["private", "group", "group-forward"],
    msg: Union[str, Message],
):
    if plugin_config.bison_use_queue:
        QUEUE.append((bot, user, user_type, msg, plugin_config.bison_resend_times))
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
            # forward_msg = Message(
            #     [
            #         MessageSegment.node_custom(
            #             group_bot_info["user_id"],
            #             nickname=group_bot_info["card"] or group_bot_info["nickname"],
            #             content=msg,
            #         )
            #         for msg in msgs
            #     ]
            # )
            # FIXME: Because of https://github.com/nonebot/adapter-onebot/issues/9

            forward_msg = [
                {
                    "type": "node",
                    "data": {
                        "name": group_bot_info["card"] or group_bot_info["nickname"],
                        "uin": group_bot_info["user_id"],
                        "content": msg,
                    },
                }
                for msg in msgs
            ]

            await _send_msgs_dispatch(bot, user, "group-forward", forward_msg)
