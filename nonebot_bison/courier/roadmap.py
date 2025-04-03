from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, NamedTuple

from .parcel import Address, Parcel

if TYPE_CHECKING:
    from .channel import ChannelName

type DeliveryReceiver[T, R] = Callable[[Parcel[T]], Awaitable[Parcel[R] | None]]


class Road(NamedTuple):
    channel: ChannelName
    receiver: DeliveryReceiver[Any, Any]

    def __repr__(self) -> str:
        return f"Road(channel={self.channel}, receiver={self.receiver.__name__})"


type Roadmaps = dict[Address, Road]
