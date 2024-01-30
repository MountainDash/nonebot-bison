import anyio

from .model import Parcel
from .meta import ConveyorMeta


class Conveyor(metaclass=ConveyorMeta):
    def __init__(self, name: str, max_buffer: int = 0):
        self.name = name
        self._send_channel, self._receive_channel = anyio.create_memory_object_stream(
            max_buffer_size=max_buffer, item_type=Parcel
        )

    async def put(self, parcel: Parcel):
        async with self._send_channel.clone() as send_channel:
            await send_channel.send(parcel)

    def get_nowait(self) -> Parcel:
        return self._receive_channel.receive_nowait()

    async def get_forever(self):
        async with self._receive_channel.clone() as receive_channel:
            async for parcel in receive_channel:
                yield parcel

    async def shutdown(self):
        await self._send_channel.aclose()
        await self._receive_channel.aclose()

    def statistics(self):
        return self._send_channel.statistics(), self._receive_channel.statistics()
