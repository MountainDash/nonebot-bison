from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import reprlib
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict
from venv import logger

from anyio import Event

type Address = str
type Metadata = dict[str, Any]


class DeliveryStatus(StrEnum):
    DELIVERED = "DELIVERED"
    DELIVERING = "DELIVERING"
    DEAD = "DEAD"


if TYPE_CHECKING:

    class _HandStamps(TypedDict, extra_items=str):
        DEAD_REASON: NotRequired[str]
        ADDRESS_CHAIN: NotRequired[list[str]]
else:

    class _HandStamps(TypedDict):
        DEAD_REASON: NotRequired[str]
        ADDRESS_CHAIN: NotRequired[list[str]]


class DeliveryReceipt:
    def __init__(self):
        self._event = Event()
        self._delivery_status: DeliveryStatus = DeliveryStatus.DELIVERING
        self._handstamps: _HandStamps = {}

    @property
    def __protected_key(self):
        return {"DEAD_REASON", "ADDRESS_CHAIN"}

    @property
    def delivery_status(self) -> DeliveryStatus:
        return self._delivery_status

    @property
    def is_delivered(self) -> bool:
        return self._delivery_status == DeliveryStatus.DELIVERED

    @property
    def is_dead(self) -> bool:
        return self._delivery_status == DeliveryStatus.DEAD

    async def wait_delivery(self):
        await self._event.wait()

    def mark_as_delivered(self):
        if not self.is_dead:
            self._delivery_status = DeliveryStatus.DELIVERED
            logger.info(f"Parcel marked as delivered: {self._handstamps}")
        else:
            logger.warning("Attempted to mark a dead parcel as delivered, ignoring")
        self._event.set()

    def mark_as_dead(self, reason: str):
        logger.warning(f"Parcel marked as dead: {reason}")
        self._delivery_status = DeliveryStatus.DEAD
        self._handstamps.update(DEAD_REASON=reason)
        self._event.set()

    @property
    def post_done_event(self):
        """等待投递完成"""
        return self._event

    def __getitem__(self, key: str):
        return self._handstamps[key]

    def __setitem__(self, key: str, value: Any):
        if key in self.__protected_key:
            raise KeyError(f"Key '{key}' is not setable, it a protected handstamp key, use sepecific methods")
        self._handstamps[key] = value

    @property
    def dead_reason(self) -> str:
        return self._handstamps.get("DEAD_REASON", "")

    @property
    def address_chain(self) -> list[str]:
        return self._handstamps.get("ADDRESS_CHAIN", [])

    @property
    def handstamps(self) -> _HandStamps:
        return self._handstamps

    def append_address(self, addr: str):
        if "ADDRESS_CHAIN" not in self._handstamps:
            self._handstamps.update(ADDRESS_CHAIN=[addr])
        else:
            self._handstamps["ADDRESS_CHAIN"].append(addr)

    def __str__(self):
        return f"{self.__class__.__name__}(delivery_status={self.delivery_status}, handstamps={self._handstamps})"


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
