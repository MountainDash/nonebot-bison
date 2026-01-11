from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple
import weakref

from loguru import logger

from .middleware import Middleware
from .parcel import DeliveryStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from anyio.streams.memory import (
        MemoryObjectReceiveStream,
        MemoryObjectSendStream,
    )

    from .middleware import Instrumentation
    from .parcel import DeliveryReceipt, Parcel
    from .types import ChannelName


class Conveyor[T](NamedTuple):
    entrance: MemoryObjectSendStream[T]
    outlet: MemoryObjectReceiveStream[T]


@dataclass(eq=False)
class Channel[T]:
    name: ChannelName
    conveyor: Conveyor[Parcel[T]]
    dead_letter_entrance: MemoryObjectSendStream[Parcel[T]] | None = None
    instrumentation: Instrumentation | None = None

    async def delivery(self) -> AsyncIterator[Parcel[T]]:
        async with self._get_receiver() as rx:
            async for parcel in rx:
                if self.instrumentation:
                    await self.instrumentation.on_delivery(parcel)

                if cm := Middleware.channels.get(self.name):
                    parcel = await cm.post_process(parcel)

                yield parcel

                parcel.receipt.mark_as_delivered()

    async def post(self, parcel: Parcel[T]) -> weakref.ReferenceType[DeliveryReceipt]:
        if not parcel.is_sendable():
            raise ValueError(f"Parcel {parcel!r} is not sendable")
        logger.debug(f"Parcel {parcel!s} is being sent by channel {self.name}")

        receipt = parcel.receipt
        try:
            sender = self._get_sender()
            await sender.send(parcel)
        except Exception as e:
            logger.error("Failed to send parcel", exc_info=e)
            await self._recycle_dead_letter(parcel)
            # 这里不需要抛出异常，因为我们已经处理了死信逻辑
            # 但仍然需要返回收据，以便调用者可以获取投递状态

        return weakref.ref(receipt)

    def _get_sender(self) -> MemoryObjectSendStream[Parcel[T]]:
        return self.conveyor.entrance

    def _get_receiver(self) -> MemoryObjectReceiveStream[Parcel[T]]:
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
        if self.dead_letter_entrance:
            self.dead_letter_entrance.close()
        self.dead_letter_entrance = None
        logger.info(f"Courier [{self.name}] closed")
