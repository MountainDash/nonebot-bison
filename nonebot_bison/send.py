from typing import NamedTuple

import anyio
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.log import logger
from nonebot_plugin_saa import AggregatedMessageFactory, MessageFactory, PlatformTarget
from nonebot_plugin_saa.auto_select_bot import refresh_bots

from .plugin_config import plugin_config

Sendable = MessageFactory | AggregatedMessageFactory


class MessageQueueItem(NamedTuple):
    send_to: PlatformTarget
    message: Sendable
    retry: int


class SendStream(NamedTuple):
    entrance: MemoryObjectSendStream[MessageQueueItem]
    outlet: MemoryObjectReceiveStream[MessageQueueItem]

    @classmethod
    def build(cls, max_buffer_size: int):
        return cls(*anyio.create_memory_object_stream[MessageQueueItem](max_buffer_size=max_buffer_size))

    def close(self):
        self.entrance.close()


_SEND_STREAM: SendStream | None = None


def set_global_send_stream(stream: SendStream):
    global _SEND_STREAM
    _SEND_STREAM = stream


def get_global_send_stream() -> SendStream:
    global _SEND_STREAM
    if not _SEND_STREAM:
        raise Exception("need to set global send stream first.")
    return _SEND_STREAM


MESSGE_SEND_INTERVAL = plugin_config.bison_send_message_interval


async def _do_send(send_target: PlatformTarget, msg: Sendable):
    try:
        await msg.send_to(send_target)
    except ActionFailed:  # TODO: catch exception of other adapters
        await refresh_bots()
        logger.warning("send msg failed, refresh bots")


async def _send_msgs_dispatch(send_target: PlatformTarget, msg: Sendable):
    if plugin_config.bison_use_queue:
        await get_global_send_stream().entrance.send(
            MessageQueueItem(send_target, msg, plugin_config.bison_resend_times)
        )
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


async def _run_send_msgs_receiver():
    logger.info("Start receive sendable message...")
    async for send_to, message, retry in get_global_send_stream().outlet:
        try:
            await _do_send(send_to, message)
        except Exception as e:
            await anyio.sleep(MESSGE_SEND_INTERVAL.total_seconds())
            if retry > 0:
                # reput to entrance
                await get_global_send_stream().entrance.send(MessageQueueItem(send_to, message, retry - 1))
            else:
                logger.warning(f"send msg err [{e}]: {message:<500}")
        else:
            await anyio.sleep(MESSGE_SEND_INTERVAL.total_seconds())
        finally:
            logger.debug(f"send to [{send_to}], message: {message}, retry: {retry}")


async def background_run_send_msgs_receiver(tg: TaskGroup):
    send_stream = SendStream.build(plugin_config.bison_send_message_max_buffer_size)
    set_global_send_stream(send_stream)

    tg.start_soon(_run_send_msgs_receiver)

    return get_global_send_stream().close
