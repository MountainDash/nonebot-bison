from typing import Literal
from dataclasses import dataclass

from nonebot_plugin_saa import MessageFactory, PlatformTarget

from nonebot_bison.delivery.registry import DefaultConveyor

from .base import ParcelLabel, ParcelHeader, ParcelPayload


@dataclass(kw_only=True)
class MessageHeader(ParcelHeader):
    """Message的头部信息, 是用来确定发送目标的部分"""

    target: PlatformTarget
    """Message的发送目标"""

    label: Literal[ParcelLabel.MESSAGE] = ParcelLabel.MESSAGE
    conveyor: Literal[DefaultConveyor.SEND] = DefaultConveyor.SEND


@dataclass
class MessagePayload(ParcelPayload):
    """Message的内容信息, 是会被发送的部分"""

    content: list[MessageFactory]
