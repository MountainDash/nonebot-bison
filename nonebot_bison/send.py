from typing import NamedTuple

import anyio
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.log import logger
from nonebot_plugin_saa import AggregatedMessageFactory, MessageFactory, PlatformTarget
from nonebot_plugin_saa.auto_select_bot import refresh_bots

from nonebot_bison.courier import Courier, Parcel
from nonebot_bison.post.abstract_post import SendableMessages

from .plugin_config import plugin_config

Sendable = MessageFactory | AggregatedMessageFactory


class MessageQueueItem(NamedTuple):
    send_to: PlatformTarget
    message: Sendable
    retry: int


MESSAGE_STREAM_ENTRANCE, MESSAGE_STREAM_OUTLET = anyio.create_memory_object_stream[MessageQueueItem](
    plugin_config.bison_max_concurrency.send_message
)

MESSGE_SEND_INTERVAL = plugin_config.bison_max_concurrency.resend_wait


async def message_stream_close():
    await MESSAGE_STREAM_ENTRANCE.aclose()
    await MESSAGE_STREAM_OUTLET.aclose()


async def _do_send(send_target: PlatformTarget, msg: Sendable):
    try:
        await msg.send_to(send_target)
    except ActionFailed:  # TODO: catch exception of other adapters
        await refresh_bots()
        logger.warning("send msg failed, refresh bots")


async def run_send_msgs_receiver():
    async for send_to, message, retry in MESSAGE_STREAM_OUTLET:
        try:
            await _do_send(send_to, message)
        except Exception as e:
            await anyio.sleep(MESSGE_SEND_INTERVAL.total_seconds())
            if retry > 0:
                # reput to entrance
                await MESSAGE_STREAM_ENTRANCE.send(MessageQueueItem(send_to, message, retry - 1))
            else:
                msg_str = str(message)
                if len(msg_str) > 50:
                    msg_str = f"{msg_str[:50]}..."
                logger.warning(f"send msg err {e} {msg_str}")
        else:
            await anyio.sleep(MESSGE_SEND_INTERVAL.total_seconds())
        finally:
            logger.debug(f"send to [{send_to}], message: {message}, retry: {retry}")


async def _send_msgs_dispatch(send_target: PlatformTarget, msg: Sendable):
    if plugin_config.bison_use_queue:
        await MESSAGE_STREAM_ENTRANCE.send(MessageQueueItem(send_target, msg, plugin_config.bison_resend_times))
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


@Courier.receive_from("message", channel="send")
async def handle_msg(parcel: Parcel[list[SendableMessages]]):
    if not parcel.metadata or parcel.metadata["send_to"]:
        raise parcel.DeliveryReject("Parcel metadata must contain 'send_to'")

    send_to: PlatformTarget = parcel.metadata["send_to"]
    async with anyio.create_task_group() as tg:
        for msgs in parcel.payload:
            # 保证顺序发送
            await tg.start(send_msgs, send_to, msgs)
