import asyncio
from collections import deque

from nonebot.log import logger
from nonebot_plugin_saa.auto_select_bot import refresh_bots
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot_plugin_saa import MessageFactory, PlatformTarget, AggregatedMessageFactory

from .plugin_config import plugin_config

Sendable = MessageFactory | AggregatedMessageFactory

QUEUE: deque[tuple[PlatformTarget, Sendable, int]] = deque()

MESSGE_SEND_INTERVAL = 1.5


async def _do_send(send_target: PlatformTarget, msg: Sendable):
    try:
        await msg.send_to(send_target)
    except ActionFailed:  # TODO: catch exception of other adapters
        await refresh_bots()
        logger.warning("send msg failed, refresh bots")


async def do_send_msgs():
    if not QUEUE:
        return
    while True:
        # why read from queue then pop item from queue?
        # if there is only 1 item in queue, pop it and await send
        # the length of queue will be 0.
        # At that time, adding items to queue will trigger a new execution of this func, which is not expected.
        # So, read from queue first then pop from it
        send_target, msg_factory, retry_time = QUEUE[0]
        try:
            await _do_send(send_target, msg_factory)
        except Exception as e:
            await asyncio.sleep(MESSGE_SEND_INTERVAL)
            QUEUE.popleft()
            if retry_time > 0:
                QUEUE.appendleft((send_target, msg_factory, retry_time - 1))
            else:
                msg_str = str(msg_factory)
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


async def _send_msgs_dispatch(send_target: PlatformTarget, msg: Sendable):
    if plugin_config.bison_use_queue:
        QUEUE.append((send_target, msg, plugin_config.bison_resend_times))
        # len(QUEUE) before append was 0
        if len(QUEUE) == 1:
            asyncio.create_task(do_send_msgs())
    else:
        await _do_send(send_target, msg)


async def send_msgs(send_target: PlatformTarget, msgs: list[MessageFactory]):
    if not plugin_config.bison_use_pic_merge:
        for msg in msgs:
            await _send_msgs_dispatch(send_target, msg)
        return
    msgs = msgs.copy()
    if plugin_config.bison_use_pic_merge == 1:
        await _send_msgs_dispatch(send_target, msgs.pop(0))
    if msgs:
        if len(msgs) == 1:  # 只有一条消息序列就不合并转发
            await _send_msgs_dispatch(send_target, msgs.pop(0))
        else:
            forward_message = AggregatedMessageFactory(list(msgs))
            await _send_msgs_dispatch(send_target, forward_message)
