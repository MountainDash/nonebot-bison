from weakref import ReferenceType

import anyio
from anyio import lowlevel
from nonebot import logger
from nonebug import App
import pytest


@pytest.mark.asyncio
async def test_courier(app: App):
    from nonebot_bison.courier import (
        Address,
        Courier,
        Instrumentation,
        Middleware,
        Parcel,
        post_to_courier,
    )
    from nonebot_bison.courier.channel import Conveyor
    from nonebot_bison.courier.parcel import DeliveryReceipt, DeliveryStatus

    test_addrs = ["test1", "test2", "test3"]

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

    dead_letter_channel = Conveyor(*anyio.create_memory_object_stream())

    test1_record = {10, 20, 30}

    @Courier.receive_from("test1")
    async def test1_comsumer(parcel: Parcel[int]):
        # 接收到 test1:10 test1:20 test1:30
        logger.info(f"comsumer: {parcel}")
        assert isinstance(parcel, Parcel)
        assert parcel.tag == "test1"
        assert parcel.receipt.delivery_status == DeliveryStatus.DELIVERING
        # 这里是首站，因此地址链只有一个地址
        assert len(parcel.receipt.address_chain) == 1
        assert "c:main-a:test1" in parcel.receipt.address_chain
        # remove会要求payload是一定存在的
        test1_record.remove(parcel.payload)
        return parcel.change_to(test_addrs.pop())

    # 只有 20 会经由test1被投递到test2
    test2_record = {20}

    @Courier.receive_from("test2", channel="secondary")
    async def test2_comsumer(parcel: Parcel[int]):
        logger.info(f"comsumer: {parcel}")
        logger.info(f"{parcel.payload}")
        assert isinstance(parcel, Parcel)
        assert parcel.tag == "test2"
        assert parcel.receipt.delivery_status == DeliveryStatus.DELIVERING
        # 这里是第二站，因此地址链有两个地址
        assert len(parcel.receipt.address_chain) == 2
        assert parcel.receipt.address_chain == ["c:main-a:test1", "c:secondary-a:test2"]
        test2_record.remove(parcel.payload)

    courier = Courier(dead_letter_channel=dead_letter_channel, instrumentation=TestIns())

    dead_addrs = {"test1", "test3"}
    dead_record = {10, 30}

    @courier.receive_from_dead_letter
    async def dead_letter_comsumer(parcel: Parcel):
        logger.info(f"!!!!!!!!!!dead_letter_comsumer: {parcel}")
        assert isinstance(parcel, Parcel)
        dead_addrs.remove(parcel.tag)
        assert parcel.receipt.delivery_status == DeliveryStatus.DEAD
        assert len(parcel.receipt.address_chain) >= 2
        dead_record.remove(parcel.payload)
        assert any("c:dead" in addr for addr in parcel.receipt.address_chain)

    async def producer(addr: Address):
        for i in range(1, 4):
            parcel = Parcel(addr, i * 10)
            r = await post_to_courier(parcel)

            async def watcher(ref: ReferenceType[DeliveryReceipt]):
                r = ref()
                if not r:
                    raise ValueError("Reference is None")
                while not r.post_done_event.is_set():
                    rr = ref()
                    logger.info(f"watcher: {rr}")
                    await lowlevel.checkpoint()
                else:
                    logger.info(f"watcher done: {r}")

            async with anyio.create_task_group() as th:
                if r:
                    th.start_soon(watcher, r)
                else:
                    raise ValueError("Failed to post parcel")

            await anyio.sleep(3)

    async with anyio.create_task_group() as tg:
        tg.start_soon(courier.run)
        tg.start_soon(producer, "test1")
        await anyio.sleep(10)
        tg.cancel_scope.cancel()
