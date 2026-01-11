from typing import TYPE_CHECKING

from anyio.abc import TaskGroup
from nonebot import get_driver, require

from .send import SendableMessages, message_stream_close, send_msgs

require("nonebot_plugin_saa")
require("nonebot_bison")

from nonebot_bison.core.courier import Courier, Parcel

if TYPE_CHECKING:
    from nonebot_plugin_saa import PlatformTarget


@Courier.receive_from("message", channel="send")
async def handle_msg(tg: TaskGroup, parcel: Parcel[list[SendableMessages]]):
    if not parcel.metadata or parcel.metadata["send_to"]:
        raise parcel.DeliveryReject("Parcel metadata must contain 'send_to'")

    send_to: PlatformTarget = parcel.metadata["send_to"]

    for msgs in parcel.payload:
        # 保证顺序发送
        await tg.start(send_msgs, send_to, msgs)


get_driver().on_shutdown(message_stream_close)
