from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
import reprlib
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, NotRequired, TypedDict
import weakref

import anyio
from anyio import Event, create_memory_object_stream
from loguru import logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from anyio.streams.memory import (
        MemoryObjectReceiveStream,
        MemoryObjectSendStream,
    )

type Address = str
type Metadata = dict[str, Any]


class HandStamp(TypedDict):
    DEAD_REASON: NotRequired[str]
    ADDRESS_CHAIN: NotRequired[list[str]]
    # PEP728 ealier version
    __extra_items__: str


class DeliveryReceipt:
    def __init__(self):
        self._event = Event()
        self.delivery_status: DeliveryStatus = DeliveryStatus.DELIVERING
        self._handstamps: HandStamp = {}  # pyright: ignore[reportAttributeAccessIssue]

    async def wait_delivery(self):
        await self._event.wait()

    def mark_as_delivered(self):
        self._is_delivered = DeliveryStatus.DELIVERED
        self._event.set()

    def mark_as_dead(self, reason: str):
        self.delivery_status = DeliveryStatus.DEAD
        self.add_handstamp("DEAD_REASON", reason)
        self._event.set()

    def add_handstamp(self, key: str, value: Any):
        self._handstamps[key] = value

    @property
    def dead_reason(self) -> str:
        return self._handstamps.get("DEAD_REASON", "")

    @property
    def address_chain(self) -> list[str]:
        return self._handstamps.get("ADDRESS_CHAIN", [])

    @property
    def handstamps(self) -> HandStamp:
        return self._handstamps

    def append_address(self, addr: str):
        if "RECEIVER_CHAIN" not in self._handstamps:
            self.add_handstamp("ADDRESS_CHAIN", [addr])
        else:
            self._handstamps["ADDRESS_CHAIN"].append(addr)

    def __str__(self):
        return f"DeliveryReceipt(delivery_status={self.delivery_status}, handstamps={self._handstamps})"


@dataclass(match_args=True, frozen=True)
class Parcel[T]:
    tag: Address
    payload: T
    metadata: Metadata | None = None
    receipt: DeliveryReceipt = field(init=False, default_factory=DeliveryReceipt)

    def change_to(self, address: Address) -> Parcel[T]:
        """生成一个新的包裹，将当前包裹的地址修改到指定地址，同时重置收据，保留地址链"""
        parcel = Parcel(address, self.payload, self.metadata)
        parcel.receipt._handstamps["ADDRESS_CHAIN"] = self.receipt.address_chain
        return parcel

    def is_sendable(self) -> bool:
        return self.receipt.delivery_status == DeliveryStatus.DELIVERING

    def __str__(self):
        return (
            f"Parcel(tag={self.tag}, payload={reprlib.repr(self.payload)}, "
            f"metadata={self.metadata}, receipt={self.receipt})"
        )


class DeliveryStatus(StrEnum):
    DELIVERED = "DELIVERED"
    DELIVERING = "DELIVERING"
    DEAD = "DEAD"


type DeliveryReceiver[T] = Callable[[Parcel[T]], Awaitable[Parcel | None]]


@dataclass
class DeliveryRoad[T]:
    receiver: DeliveryReceiver[T]
    _channel: Channel[T] | None = field(init=False, default=None)

    def connect(self, channel: Channel[T]):
        self._channel = channel

    @property
    def channel(self) -> Channel[T]:
        if not self._channel:
            raise ValueError("Channel is not connected")
        return self._channel


class Conveyor[T](NamedTuple):
    entrance: MemoryObjectSendStream[T]
    outlet: MemoryObjectReceiveStream[T]


class Middleware(ABC):
    STORED_MIDDLEWARES: ClassVar[dict[Address, Middleware]] = {}

    # a class decorator for registering middleware
    @classmethod
    def for_address(cls, address: str):
        def wrapper(middleware_cls):
            cls.add(address, middleware_cls())
            return middleware_cls

        return wrapper

    @classmethod
    def add(cls, address: str, middleware: Middleware):
        cls.STORED_MIDDLEWARES[address] = middleware

    @abstractmethod
    async def pre_process[T](self, parcel: Parcel[T]) -> Parcel[T]: ...

    @abstractmethod
    async def post_process[T](self, parcel: Parcel[T]) -> Parcel[T]: ...


class Instrumentation(ABC):
    @abstractmethod
    async def on_delivery(self, parcel: Parcel): ...

    @abstractmethod
    async def on_process_dead_parcel(self, parcel: Parcel): ...


@dataclass(eq=False)
class Channel[T]:
    address: Address
    conveyor: Conveyor[Parcel[T]]
    dead_letter_entrance: MemoryObjectSendStream[Parcel[T]] | None = None
    instrumentation: Instrumentation | None = None

    def __post_init__(self):
        self.middleware = Middleware.STORED_MIDDLEWARES.get(self.address)

    async def delivery(self) -> AsyncIterator[Parcel[T]]:
        rx = await self._get_receiver()
        async with rx:
            async for parcel in rx:
                if self.instrumentation:
                    await self.instrumentation.on_delivery(parcel)

                if self.middleware:
                    parcel = await self.middleware.post_process(parcel)

                yield parcel

                parcel.receipt.mark_as_delivered()

    async def post(self, parcel: Parcel[T]) -> weakref.ReferenceType[DeliveryReceipt]:
        if not parcel.is_sendable():
            raise ValueError(f"Parcel {parcel!r} is not sendable")
        if parcel.tag != self.address:
            logger.warning(f"Parcel {parcel!r} is not for this channel")
            await self._recycle_dead_letter(parcel)

        receipt = parcel.receipt
        try:
            sender = await self._get_sender()
            await sender.send(parcel)
        except Exception as e:
            logger.error("Failed to send parcel", exc_info=e)
            await self._recycle_dead_letter(parcel)

        return weakref.ref(receipt)

    async def _get_sender(self) -> MemoryObjectSendStream[Parcel[T]]:
        return self.conveyor.entrance

    async def _get_receiver(self) -> MemoryObjectReceiveStream[Parcel[T]]:
        return self.conveyor.outlet

    async def _recycle_dead_letter(self, dead_letter: Parcel[T]):
        logger.warning(f"recycling dead letter {dead_letter!s} on channel")
        already_dead = dead_letter.receipt.delivery_status == DeliveryStatus.DEAD
        if not already_dead:
            dead_letter.receipt.mark_as_dead("No receiver found")
        else:
            logger.warning(f"Dead letter {dead_letter!s} was already dead, but received again")
            return

        if self.instrumentation:
            await self.instrumentation.on_process_dead_parcel(dead_letter)

        if self.dead_letter_entrance:
            await self.dead_letter_entrance.send(dead_letter)

    def close(self):
        self._get_sender().close()
        if self.dead_letter_stream:
            self.dead_letter_stream.entrance.close()
        self.dead_letter_stream = None
        logger.info("Courier closed")


_post_channel_entrance, _post_channel_outlet = create_memory_object_stream()


async def post_to_couier[T](parcel: Parcel[T]):
    if _post_channel_entrance.statistics().open_receive_streams == 0:
        logger.warning("No courier is running")
        return

    await _post_channel_entrance.send(parcel)


@dataclass(eq=False)
class Courier:
    roadmaps: ClassVar[dict[Address, DeliveryRoad]] = {}
    instrumentation: Instrumentation | None = None
    dead_letter_channel: tuple[MemoryObjectSendStream[Parcel[Any]], MemoryObjectReceiveStream[Parcel[Any]]] | None = (
        None
    )

    def __post_init__(self):
        self.dead_letter_receiver: DeliveryReceiver[Any] | None = None
        self.close_event = anyio.Event()

        for address in self.roadmaps:
            road = self.roadmaps[address]
            road.connect(self._create_channel(address))

    @classmethod
    def receive_from(cls, address: Address):
        """注册一个包裹的接收者，该被注册的可调用对象将会用于处理特定地址的包裹

        通过返回一个新的包裹，可以将包裹传递给下一个接收者
        - 如果返回的包裹的地址和原包裹的地址相同，将会被丢弃
        - 如果返回的包裹的地址和原包裹的地址不同，将会被投递到新的地址
        - 如果返回 None，本次投递结束
        """
        if address in cls.roadmaps:
            raise ValueError(f"Receiver for {address} already has been registered")

        def wrapper[T](receiver: DeliveryReceiver[T]) -> DeliveryReceiver[T]:
            cls.roadmaps[address] = DeliveryRoad(receiver)
            return receiver

        return wrapper

    async def post(self, parcel: Parcel[Any]):
        """投递一个包裹"""
        if not parcel.is_sendable():
            raise ValueError(f"Parcel {parcel!s} is not sendable")

        if parcel.tag not in self.roadmaps:
            await self._recycle_dead_letter(parcel)
            return

        if Middleware.STORED_MIDDLEWARES.get(parcel.tag):
            parcel = await Middleware.STORED_MIDDLEWARES[parcel.tag].pre_process(parcel)

        road = self.roadmaps.get(parcel.tag)
        if not road:
            logger.warning(f"No receiver found for parcel {parcel!s}")
            await self._recycle_dead_letter(parcel)
            return

        receipt = await road.channel.post(parcel)
        return receipt

    def receive_from_dead_letter(self, receiver: DeliveryReceiver[Any]):
        """注册一个死信接收者"""

        if not self.dead_letter_channel:
            raise ValueError("Dead letter channel is not available")

        self.dead_letter_receiver = receiver
        return receiver

    async def run(self):
        """开始运行"""

        async def _run_global_post_receiver():
            async with _post_channel_outlet:
                async for parcel in _post_channel_outlet:
                    await self.post(parcel)

        async def _run_roadmap(road: DeliveryRoad):
            async for parcel in road.channel.delivery():
                parcel.receipt.append_address(road.channel.address)
                match await road.receiver(parcel):
                    case None:
                        continue
                    case Parcel(tag) if tag == parcel.tag:
                        logger.warning(f"Receiver {road.receiver} returned a parcel with the same tag, recycling")
                        await self._recycle_dead_letter(parcel)
                    case Parcel() as new_parcel:
                        logger.debug(f"Receiver {road.receiver} returned a new parcel: {new_parcel!s}, forwarding")
                        await self.post(new_parcel)
                    case other:
                        logger.error(f"Receiver returned an unexpected value: {other!r}")

        async def _run_dead_letter_receiver():
            if self.dead_letter_receiver and self.dead_letter_channel:
                async with self.dead_letter_channel[1] as rx:
                    async for dead_letter in rx:
                        await self.dead_letter_receiver(dead_letter)

        async with anyio.create_task_group() as tg:
            for _, road in self.roadmaps.items():
                tg.start_soon(_run_roadmap, road)

            tg.start_soon(_run_dead_letter_receiver)
            tg.start_soon(_run_global_post_receiver)

            await self.close_event.wait()
            tg.cancel_scope.cancel()

    async def close(self):
        """关闭"""
        for road in self.roadmaps.values():
            road.channel.close()
        if self.dead_letter_channel:
            self.dead_letter_channel[0].close()
        self.close_event.set()

    async def _recycle_dead_letter(self, dead_letter: Parcel[Any]):
        logger.warning(f"recycling dead letter {dead_letter!s} on courier")
        already_dead = dead_letter.receipt.delivery_status == DeliveryStatus.DEAD
        if not already_dead:
            dead_letter.receipt.mark_as_dead("No receiver found")
        else:
            logger.warning(f"Dead letter {dead_letter!s} was already dead, but received again")
            return

        if self.dead_letter_receiver and self.dead_letter_channel:
            await self.dead_letter_channel[0].send(dead_letter)

    def _create_channel(self, address: Address) -> Channel:
        entrance, outlet = create_memory_object_stream()
        return Channel(
            address=address,
            conveyor=Conveyor(entrance, outlet),
            dead_letter_entrance=self.dead_letter_channel[0] if self.dead_letter_channel else None,
            instrumentation=self.instrumentation,
        )
