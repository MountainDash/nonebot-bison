import asyncio

from nonebot.log import logger
from nonebot_plugin_saa.utils.exceptions import NoBotFound
from nonebot_plugin_saa.auto_select_bot import refresh_bots
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot_plugin_saa import MessageFactory, PlatformTarget, AggregatedMessageFactory

from ..plugin_config import plugin_config
from .queue import DELIVERY_QUEUE, DELIVERY_INTERVAL, MESSAGE_SEND_QUEUE, MESSAGE_SEND_INTERVAL, Sendable


async def _do_send(send_target: PlatformTarget, msg: Sendable):
    try:
        await msg.send_to(send_target)
    except ActionFailed:  # TODO: catch exception of other adapters
        await refresh_bots()
        logger.warning("send msg failed, refresh bots")


async def do_send_msgs():
    if not MESSAGE_SEND_QUEUE:
        return
    while True:
        # why read from queue then pop item from queue?
        # if there is only 1 item in queue, pop it and await send
        # the length of queue will be 0.
        # At that time, adding items to queue will trigger a new execution of this func, which is not expected.
        # So, read from queue first then pop from it
        send_target, msg_factory, retry_time = MESSAGE_SEND_QUEUE[0]
        try:
            await _do_send(send_target, msg_factory)
        except Exception as e:
            await asyncio.sleep(MESSAGE_SEND_INTERVAL)
            MESSAGE_SEND_QUEUE.popleft()
            if retry_time > 0:
                MESSAGE_SEND_QUEUE.appendleft((send_target, msg_factory, retry_time - 1))
            else:
                msg_str = str(msg_factory)
                if len(msg_str) > 50:
                    msg_str = msg_str[:50] + "..."
                logger.warning(f"send msg err {e} {msg_str}")
        else:
            # sleeping after popping may also cause re-execution error like above mentioned
            await asyncio.sleep(MESSAGE_SEND_INTERVAL)
            MESSAGE_SEND_QUEUE.popleft()
        finally:
            if not MESSAGE_SEND_QUEUE:
                return


async def _send_msgs_dispatch(send_target: PlatformTarget, msg: Sendable):
    if plugin_config.bison_use_queue:
        MESSAGE_SEND_QUEUE.append((send_target, msg, plugin_config.bison_resend_times))
        # len(QUEUE) before append was 0
        if len(MESSAGE_SEND_QUEUE) == 1:
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


async def parcel_deliver():
    """将 Parcel 发送出去"""
    while True:
        logger.info("checking deliver deque...")
        if not DELIVERY_QUEUE:
            await asyncio.sleep(DELIVERY_INTERVAL + 1)
            continue

        parcel = DELIVERY_QUEUE[0]
        try:
            await send_msgs(*parcel.gen_sendable())
        except NoBotFound:
            logger.warning("no bot connected")
        except Exception as e:
            logger.exception(f"deliver parcel err: {e}")
        finally:
            DELIVERY_QUEUE.popleft()
            await asyncio.sleep(DELIVERY_INTERVAL)
