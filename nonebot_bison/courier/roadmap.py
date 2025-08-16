from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, NamedTuple

from nonebot.dependencies import Dependent

from .parcel import Parcel
from .types import Address

if TYPE_CHECKING:
    from .types import ChannelName

type DeliveryReceiver[R] = Dependent[Parcel[R] | None]
type DeliveryReceiverHandle[R] = Callable[..., Parcel[R] | None] | Callable[..., Awaitable[Parcel[R] | None]]


class Road(NamedTuple):
    channel: ChannelName
    receiver: DeliveryReceiver[Any]

    def __repr__(self) -> str:
        return f"Road(channel={self.channel}, receiver={self.receiver})"


type Roadmaps = dict[Address, Road]
