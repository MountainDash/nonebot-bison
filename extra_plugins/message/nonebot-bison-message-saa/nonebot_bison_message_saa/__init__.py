from typing import TYPE_CHECKING

from anyio.abc import TaskGroup
from nonebot import get_driver, logger, require

from .send import message_stream_close, run_send_msgs_receiver, send_msgs

require("nonebot_plugin_saa")
require("nonebot_bison")
from nonebot_plugin_saa import MessageFactory, enable_auto_select_bot

from nonebot_bison.core.courier import Courier, Parcel

if TYPE_CHECKING:
    from nonebot_plugin_saa import PlatformTarget

enable_auto_select_bot()

@Courier.receive_from("message", channel="send")
async def handle_msg(tg: TaskGroup, parcel: Parcel[str]):
    if not parcel.metadata or "send_to" not in parcel.metadata:
        logger.warning(f"{parcel.metadata}, {("send_to" in parcel.metadata)=}")
        raise parcel.DeliveryReject("Parcel metadata must contain 'send_to'")

    send_to: PlatformTarget = parcel.metadata["send_to"]

    await tg.start(send_msgs, send_to, [MessageFactory(parcel.payload)])

d = get_driver()

@d.on_startup
async def _():
    d.task_group.start_soon(run_send_msgs_receiver)

d.on_shutdown(message_stream_close)
