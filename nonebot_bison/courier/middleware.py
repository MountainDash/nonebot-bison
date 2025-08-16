from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from .channel import ChannelName
    from .parcel import Parcel
    from .types import Address


class Instrumentation(ABC):
    @abstractmethod
    async def on_delivery(self, parcel: Parcel): ...

    @abstractmethod
    async def on_process_dead_parcel(self, parcel: Parcel): ...


class Middleware(ABC):
    addresses: ClassVar[dict[Address, Middleware]] = {}
    channels: ClassVar[dict[ChannelName, Middleware]] = {}

    # a class decorator for registering middleware
    @classmethod
    def for_address(cls, address: str):
        def wrapper(middleware_cls):
            cls.addresses[address] = middleware_cls()
            return middleware_cls

        return wrapper

    @classmethod
    def for_channel(cls, channel: str):
        def wrapper(middleware_cls):
            cls.channels[channel] = middleware_cls()
            return middleware_cls

        return wrapper

    @abstractmethod
    async def pre_process[T](self, parcel: Parcel[T]) -> Parcel[T]: ...

    @abstractmethod
    async def post_process[T](self, parcel: Parcel[T]) -> Parcel[T]: ...
