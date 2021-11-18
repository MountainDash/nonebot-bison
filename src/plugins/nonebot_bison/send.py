import time

from nonebot import logger
from nonebot.adapters.cqhttp.bot import Bot

from .plugin_config import plugin_config

QUEUE = []
LAST_SEND_TIME = time.time()

async def _do_send(bot: 'Bot', user: str, user_type: str, msg):
    if user_type == 'group':
        await bot.call_api('send_group_msg', group_id=user, message=msg)
    elif user_type == 'private':
        await bot.call_api('send_private_msg', user_id=user, message=msg)

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
                    msg_str = msg_str[:50] + '...'
                logger.warning(f'send msg err {e} {msg_str}')
        LAST_SEND_TIME = time.time()

async def send_msgs(bot, user, user_type, msgs):
    if plugin_config.bison_use_queue:
        for msg in msgs:
            QUEUE.append((bot, user, user_type, msg, 2))
    else:
        for msg in msgs:
            await _do_send(bot, user, user_type, msg)


