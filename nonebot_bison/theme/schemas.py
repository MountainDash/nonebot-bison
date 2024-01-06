from dataclasses import dataclass

from nonebot_plugin_saa import MessageFactory, PlatformTarget


@dataclass
class ParcelHeader:
    """Parcel的头部信息, 是用来确定发送目标的部分"""

    target: PlatformTarget
    """Parcel的发送目标"""


@dataclass
class ParcelPayload:
    """Parcel的内容信息, 是会被发送的部分"""

    content: list[MessageFactory]


@dataclass
class Parcel:
    header: ParcelHeader
    payload: ParcelPayload

    def gen_sendable(self) -> tuple[PlatformTarget, list[MessageFactory]]:
        return self.header.target, self.payload.content
