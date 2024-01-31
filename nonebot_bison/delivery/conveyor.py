import weakref

import anyio

from nonebot_bison.types import Parcel


class ConveyorMeta(type):
    _conveyor_record: dict[str, weakref.ref["Conveyor"]] = {}

    def __call__(cls, *args, **kwargs) -> "Conveyor":
        instance = super().__call__(*args, **kwargs)
        cls._conveyor_record[instance.name] = weakref.ref(instance)
        return instance

    @classmethod
    def get_conveyor_ref(cls, name: str) -> weakref.ref["Conveyor"] | None:
        """获取传送带的弱引用"""
        return cls._conveyor_record.get(name)


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

    def get_forever(self):
        return self._receive_channel

    async def ashutdown(self):
        await self._send_channel.aclose()
        await self._receive_channel.aclose()

    def shutdown(self):
        self._send_channel.close()
        self._receive_channel.close()

    def statistics(self):
        return self._send_channel.statistics(), self._receive_channel.statistics()

    @classmethod
    async def put_to(cls, name: str, parcel: Parcel):
        if conveyor_ref := cls.get_conveyor_ref(name):
            conveyor = conveyor_ref()
            if not conveyor:
                raise RuntimeError(f"conveyor {name} not found")
            await conveyor.put(parcel)
        else:
            raise RuntimeError(f"conveyor {name} not found")
