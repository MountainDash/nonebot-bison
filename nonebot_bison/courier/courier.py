from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Self

import anyio
from anyio import create_memory_object_stream
from loguru import logger

from .channel import Channel, ChannelName, Conveyor
from .middleware import Middleware
from .parcel import Parcel
from .roadmap import Road

if TYPE_CHECKING:
    from .middleware import Instrumentation
    from .parcel import Address
    from .roadmap import DeliveryReceiver, Roadmaps


@dataclass(eq=False)
class Courier:
    roadmaps: ClassVar[Roadmaps] = {}
    plan_channels: ClassVar[set[ChannelName]] = set()
    instrumentation: Instrumentation | None = None
    dead_letter_channel: Conveyor | None = None
    channel_buffer_size: int = 100
    _instance: ClassVar[Self | None] = None

    def __new__(cls, *args, **kwargs) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> Self:
        if cls._instance is None:
            raise ValueError("Courier instance is not created yet, please call Courier() and .run() first")
        return cls._instance

    def __post_init__(self):
        self.dead_letter_receiver: DeliveryReceiver[Any, Any] | None = None
        self.close_event = anyio.Event()
        self.channels: dict[ChannelName, Channel[Any]] = {}

    @classmethod
    def receive_from(cls, address: Address, channel: ChannelName = "main"):
        """注册一个包裹的接收者，该被注册的可调用对象将会用于处理特定地址的包裹

        通过返回一个新的包裹，可以将包裹传递给下一个接收者
        - 如果返回的包裹的地址和原包裹的地址相同，将会被丢弃
        - 如果返回的包裹的地址和原包裹的地址不同，将会被投递到新的地址
        - 如果返回 None，本次投递结束
        """
        if address in cls.roadmaps:
            raise ValueError(f"Receiver for {address} already has been registered")

        def wrapper[T, R](receiver: DeliveryReceiver[T, R]) -> DeliveryReceiver[T, R]:
            cls.roadmaps[address] = Road(
                channel=channel,
                receiver=receiver,
            )
            cls.plan_channels.add(channel)
            return receiver

        return wrapper

    async def post(self, parcel: Parcel[Any]):
        """投递一个包裹"""
        if not parcel.is_sendable():
            raise ValueError(f"Parcel {parcel!s} is not sendable")

        if parcel.tag not in self.roadmaps:
            await self._recycle_dead_letter(parcel, reason=f"No roadmap found for address {parcel.tag!r}")
            return

        if pm := Middleware.addresses.get(parcel.tag):
            parcel = await pm.pre_process(parcel)

        road = self.roadmaps[parcel.tag]
        return await self.channels[road.channel].post(parcel)

    def receive_from_dead_letter(self, receiver: DeliveryReceiver[Any, Any]):
        """注册一个死信接收者"""

        if not self.dead_letter_channel:
            raise ValueError("Dead letter channel is not available")

        self.dead_letter_receiver = receiver
        return receiver

    async def run(self):
        """开始运行"""

        for channel in self.plan_channels:
            self.channels[channel] = self._create_channel(channel)

        async def _run_parcel_forwarding(channel: ChannelName):
            async for parcel in self.channels[channel].delivery():
                address = parcel.tag
                parcel.receipt.append_address(f"c:{channel}-a:{address}")
                if not (send_road := self.roadmaps.get(address)):
                    logger.warning(f"No roadmap found for parcel {parcel!s}, recycling")
                    await self._recycle_dead_letter(parcel, reason=f"No roadmap found for address {address!r}")
                    continue
                if send_road.channel != channel:
                    logger.warning(f"Roadmap channel mismatch for parcel {parcel!s}, recycling")
                    await self._recycle_dead_letter(
                        parcel, reason=f"Roadmap channel mismatch: {send_road.channel!r} != {channel!r}"
                    )
                    continue

                try:
                    match await send_road.receiver(parcel):
                        case None:
                            continue
                        case Parcel(tag) if tag == parcel.tag:
                            logger.warning(
                                f"Receiver {send_road.receiver} returned a parcel with the same tag, recycling"
                            )
                            await self._recycle_dead_letter(
                                parcel, reason=f"Receiver returned a parcel with the same tag: {tag!r}"
                            )
                            continue
                        case Parcel() as new_parcel:
                            logger.debug(
                                f"Receiver {send_road.receiver} returned a new parcel: {new_parcel!s}, forwarding"
                            )
                            await self.post(new_parcel)
                            continue
                        case other:
                            logger.error(f"Receiver returned an unexpected value: {other!r}")
                            await self._recycle_dead_letter(parcel, reason=f"Unexpected return value: {other!r}")
                            continue
                except Exception as e:
                    logger.error(
                        f"Error occurred while processing parcel {parcel!s} in receiver {send_road.receiver}",
                        exc_info=e,
                    )
                    await self._recycle_dead_letter(parcel, reason=str(e))
                    continue
                else:
                    logger.debug(f"Parcel {parcel!s} processed successfully by receiver {send_road.receiver}")

        async def _run_dead_letter_receiver():
            if self.dead_letter_receiver and self.dead_letter_channel:
                async with self.dead_letter_channel.outlet as rx:
                    async for dead_letter in rx:
                        await self.dead_letter_receiver(dead_letter)

        async with anyio.create_task_group() as tg:
            for channel in self.plan_channels:
                tg.start_soon(_run_parcel_forwarding, channel)

            tg.start_soon(_run_dead_letter_receiver)

            await self.close_event.wait()
            tg.cancel_scope.cancel()

    def close(self):
        """关闭"""
        for channel in self.channels.values():
            channel.close()
        if self.dead_letter_channel:
            self.dead_letter_channel.entrance.close()
        self.close_event.set()

    async def _recycle_dead_letter(self, dead_letter: Parcel[Any], reason: str):
        logger.warning(f"recycling dead letter {dead_letter!s} on courier")
        dead_letter.receipt.append_address(f"c:dead-a:{dead_letter.tag}")
        if not dead_letter.receipt.is_dead:
            dead_letter.receipt.mark_as_dead(reason)
        else:
            logger.warning(f"Dead letter {dead_letter!s} was already dead, but received again")
            return

        if self.dead_letter_receiver and self.dead_letter_channel:
            await self.dead_letter_channel.entrance.send(dead_letter)

    def _create_channel(self, name: str) -> Channel:
        entrance, outlet = create_memory_object_stream(max_buffer_size=self.channel_buffer_size)
        return Channel(
            name=name,
            conveyor=Conveyor(entrance, outlet),
            dead_letter_entrance=self.dead_letter_channel.entrance if self.dead_letter_channel else None,
            instrumentation=self.instrumentation,
        )
