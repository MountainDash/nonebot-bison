import time
from email import message
from typing import Literal, Union

from nonebot.adapters import Message, MessageSegment
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.log import logger

from .plugin_config import plugin_config

QUEUE = []  # 不开启图片合并转发时使用
LAST_SEND_TIME = time.time()


def generate_forward_msg(msgs: list, self_id: str, nickname: str):
    group_msg = []
    for msg in msgs:
        sub_msg = {
            "type": "node",
            "data": {"name": f"{nickname}", "uin": f"{self_id}", "content": f"{msg}"},
        }
        group_msg.append(sub_msg)

    return group_msg


async def _do_send(
    bot: "Bot", user: str, user_type: str, msg: Union[str, Message, MessageSegment]
):
    if user_type == "group":
        await bot.call_api("send_group_msg", group_id=user, message=msg)
    elif user_type == "private":
        await bot.call_api("send_private_msg", user_id=user, message=msg)


async def _do_merge_send(
    bot: Bot, user, user_type: Literal["private", "group"], msgs: list
):
    if plugin_config.bison_use_pic_merge == 1:
        try:
            await _do_send(bot, user, user_type, msgs.pop(0))  # 弹出第一条消息，剩下的消息合并
        except Exception as e_f:  # first_msg_exception
            logger.error("向群{}发送消息序列首消息失败:{}".format(user, repr(e_f)))
        else:
            logger.info("成功向群{}发送消息序列中的首条消息".format(user))
    try:
        if msgs:
            if len(msgs) == 1:  # 只有一条消息序列就不合并转发
                await _do_send(bot, user, user_type, msgs.pop(0))
            else:
                group_bot_info = await bot.get_group_member_info(
                    group_id=user, user_id=bot.self_id, no_cache=True
                )  # 调用api获取群内bot的相关参数
                forward_msg = generate_forward_msg(
                    msgs=msgs,
                    self_id=group_bot_info["user_id"],
                    nickname=group_bot_info["card"],
                )  # 生成合并转发内容
                await bot.send_group_forward_msg(group_id=user, messages=forward_msg)
    except Exception as e_b:  # behind_msg_exception
        logger.warning("向群{}发送合并图片消息超时或者可能失败:{}\n可能是因为图片太大或者太多".format(user, repr(e_b)))
    else:
        logger.info("成功向群{}发送合并图片转发消息".format(user))


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
    if plugin_config.bison_use_queue:
        if plugin_config.bison_use_pic_merge and user_type == "group":
            await _do_merge_send(bot, user, user_type, msgs)
        else:
            for msg in msgs:
                QUEUE.append((bot, user, user_type, msg, 2))

    else:
        for msg in msgs:
            await _do_send(bot, user, user_type, msg)
