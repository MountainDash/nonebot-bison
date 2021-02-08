from nonebot.adapters.cqhttp import Bot
import nonebot
from nonebot import logger
import time
import asyncio

QUEUE = []
LAST_SEND_TIME = time.time()


async def do_send_msgs():
    global LAST_SEND_TIME
    if time.time() - LAST_SEND_TIME < 1.4:
        return
    if QUEUE:
        bot, user, user_type, msg, retry_time = QUEUE.pop(0)
        try:
            if user_type == 'group':
                await bot.call_api('send_group_msg', group_id=user, message=msg)
            elif user_type == 'private':
                await bot.call_api('send_private_msg', user_id=user, message=msg)
        except:
            if retry_time > 0:
                QUEUE.insert(0, (bot, user, user_type, msg, retry_time - 1))
            else:
                logger.warning('send msg err {}'.format(msg))
        LAST_SEND_TIME = time.time()

def send_msgs(bot, user, user_type, msgs):
    for msg in msgs:
        QUEUE.append((bot, user, user_type, msg, 3))


