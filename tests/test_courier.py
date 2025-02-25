import anyio
from nonebot import logger
from nonebug import App
import pytest


@pytest.mark.asyncio
async def test_courier(app: App):
    from nonebot_bison.core.courier import (
        Address,
        Courier,
        Instrumentation,
        Middleware,
        Parcel,
        post_to_couier,
    )

    class TestIns(Instrumentation):
        async def on_delivery(self, parcel: Parcel):
            logger.info(f"on_delivery: {parcel}")

        async def on_process_dead_parcel(self, parcel: Parcel):
            logger.info(f"on_process_dead_parcel: {parcel}")

    @Middleware.for_address("test1")
    class TestMiddle(Middleware):
        async def pre_process(self, parcel: Parcel):
            logger.info(f"pre_process: {parcel}")
            return parcel

        async def post_process(self, parcel: Parcel):
            logger.info(f"post_process: {parcel}")
            return parcel

    dead_letter_entrance = anyio.create_memory_object_stream()

    test_addrs = ["test1", "test2", "test3"]

    @Courier.receive_from("test1")
    async def test1_comsumer(parcel: Parcel[int]):
        logger.info(f"comsumer: {parcel}")
        return parcel.change_to(test_addrs.pop())


    @Courier.receive_from("test2")
    async def test2_comsumer(parcel: Parcel[int]):
        logger.info(f"comsumer: {parcel}")
        logger.info(f"{parcel.payload}")

    courier = Courier(dead_letter_channel=dead_letter_entrance, instrumentation=TestIns())

    @courier.receive_from_dead_letter
    async def dead_letter_comsumer(parcel: Parcel):
        logger.info(f"!!!!!!!!!!dead_letter_comsumer: {parcel}")

    async def producer(addr: Address):
        for i in range(3):
            parcel = Parcel(addr, i * 10)
            await post_to_couier(parcel)
            await anyio.sleep(1)

    async with anyio.create_task_group() as tg:
        tg.start_soon(producer, "test1")
        tg.start_soon(courier.run)
        await anyio.sleep(5)
        tg.cancel_scope.cancel()
