from typing import cast

import anyio
from nonebot.log import logger
from nonebot_plugin_saa.utils.exceptions import NoBotFound
from nonebot_plugin_saa.auto_select_bot import refresh_bots
from nonebot.adapters.onebot.v11.exception import ActionFailed
from anyio.streams.memory import MemoryObjectSendStream, MemoryObjectReceiveStream
from nonebot_plugin_saa import MessageFactory, PlatformTarget, AggregatedMessageFactory

from nonebot_bison.types import Parcel, ParcelLabel, MessageHeader, MessagePayload

from ..plugin_config import plugin_config
from .registry import DefaultConveyor, conveyor_dispatch

MESSAGE_SEND_INTERVAL = 0.2
Sendable = MessageFactory | AggregatedMessageFactory


async def _do_send(send_target: PlatformTarget, msg: Sendable):
    try:
        await msg.send_to(send_target)
    except ActionFailed:  # TODO: catch exception of other adapters
        await refresh_bots()
        logger.warning("send msg failed, refresh bots")
    except NoBotFound as e:
        logger.error(f"send msg failed, no bot found: {e}")


async def do_send_msgs(send_channel: MemoryObjectSendStream, receive_channel: MemoryObjectReceiveStream):
    async with send_channel, receive_channel:
        async for send_target, msg_factory, retry_time in receive_channel:
            try:
                await _do_send(send_target, msg_factory)
            except Exception as e:
                await anyio.sleep(MESSAGE_SEND_INTERVAL)
                if retry_time > 0:
                    await send_channel.send((send_target, msg_factory, retry_time - 1))
                else:
                    msg_str = str(msg_factory)
                    if len(msg_str) > 50:
                        msg_str = msg_str[:50] + "..."
                    logger.warning(f"send msg err {e} {msg_str}")
            else:
                await anyio.sleep(MESSAGE_SEND_INTERVAL)


async def _send_msgs_dispatch(send_target: PlatformTarget, msg: Sendable, send_channel: MemoryObjectSendStream):
    async with send_channel:
        if plugin_config.bison_use_queue:
            await send_channel.send((send_target, msg, plugin_config.bison_resend_times))
        else:
            await _do_send(send_target, msg)


async def dispatch_msgs(send_target: PlatformTarget, msgs: list[MessageFactory], send_channel: MemoryObjectSendStream):
    if not plugin_config.bison_use_pic_merge:
        for msg in msgs:
            await _send_msgs_dispatch(send_target, msg, send_channel)
        return
    msgs = msgs.copy()
    if plugin_config.bison_use_pic_merge == 1:
        await _send_msgs_dispatch(send_target, msgs.pop(0), send_channel)
    if msgs:
        if len(msgs) == 1:  # 只有一条消息序列就不合并转发
            await _send_msgs_dispatch(send_target, msgs.pop(0), send_channel)
        else:
            forward_message = AggregatedMessageFactory(list(msgs))
            await _send_msgs_dispatch(send_target, forward_message, send_channel)


@conveyor_dispatch(DefaultConveyor.SEND, ParcelLabel.MESSAGE)
async def msg_deliver(parcel: Parcel):
    """将 Parcel 发送出去"""
    assert parcel.header.label == ParcelLabel.MESSAGE
    msg_header = cast(MessageHeader, parcel.header)
    msg_payload = cast(MessagePayload, parcel.payload)

    # (send_target, msg, plugin_config.bison_resend_times)
    async with anyio.create_task_group() as tg:
        msg_send_channel, message_receive_channel = anyio.create_memory_object_stream(5)
        async with msg_send_channel, message_receive_channel:
            tg.start_soon(do_send_msgs, msg_send_channel.clone(), message_receive_channel.clone())
            tg.start_soon(dispatch_msgs, msg_header.target, msg_payload.content, msg_send_channel.clone())
