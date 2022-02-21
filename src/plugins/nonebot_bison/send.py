from email import message
import time
from typing import List, Literal, Union

from nonebot.adapters import Message, MessageSegment
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.log import logger

from .plugin_config import plugin_config

QUEUE = []
LAST_SEND_TIME = time.time()


async def _do_send(
    bot: "Bot", user: str, user_type: str, msg: Union[str, Message, MessageSegment]
):
    if user_type == "group":
        await bot.call_api("send_group_msg", group_id=user, message=msg)
    elif user_type == "private":
        await bot.call_api("send_private_msg", user_id=user, message=msg)

async def _do_send_forward(
    bot: "Bot", user: str, msgs: list
):
    group_msg = []
    bot_info = await bot.call_api("get_login_info")#猜测返回list 第一个为user_id，第二个为nickname
    for msg in msgs:
        sub_msg = {
            "type": "node",
            "data": {
                "name": f"{bot_info[0]}",
                "uin": f"{bot_info[1]}",
                "content": msg
            }
        }
        group_msg.append(sub_msg)
    await bot.call_api("send_group_forward_msg", group_id=user, message=group_msg)

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


async def send_msgs(bot: Bot, user, user_type: Literal["private", "group"], msgs: list):
    if plugin_config.bison_use_forward_pic and user_type!="private":
        if msgs:
            _do_send_forward(bot, user, msgs)
    elif plugin_config.bison_use_queue:
        for msg in msgs:
            QUEUE.append((bot, user, user_type, msg, 2))
    else:
        for msg in msgs:
            await _do_send(bot, user, user_type, msg)
