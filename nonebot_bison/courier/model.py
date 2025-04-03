from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
import reprlib
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, NotRequired, TypedDict

from anyio import Event

if TYPE_CHECKING:
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


class DeliveryStatus(StrEnum):
    DELIVERED = "DELIVERED"
    DELIVERING = "DELIVERING"
    DEAD = "DEAD"


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


type DeliveryReceiver[T] = Callable[[Parcel[T]], Awaitable[Parcel | None]]


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
