from typing import Annotated
from weakref import ReferenceType

import anyio
from anyio import lowlevel
from nonebot import logger
from nonebot.exception import TypeMisMatch
from nonebug import App
import pytest


@pytest.mark.asyncio
async def test_courier(app: App):
    from nonebot_bison.courier import (
        Address,
        Courier,
        Instrumentation,
        Metadata,
        Middleware,
        Parcel,
        post_to_courier,
    )
    from nonebot_bison.courier.channel import Conveyor
    from nonebot_bison.courier.param import MetaFetch
    from nonebot_bison.courier.parcel import DeliveryReceipt, DeliveryStatus
    from nonebot_bison.courier.types import DEAD_REASON

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
    async def test2_comsumer(
        payload: int,
        metadata,
        meta: Metadata,
        receipt,
        rep: DeliveryReceipt,
    ):
        logger.info(f"comsumer: paylaod[{payload}]")
        logger.info(f"metadata: {metadata}")
        assert metadata is meta
        assert isinstance(receipt, DeliveryReceipt)
        assert receipt == rep
        assert receipt.delivery_status == DeliveryStatus.DELIVERING
        # 这里是第二站，因此地址链有两个地址
        assert len(receipt.address_chain) == 2
        assert receipt.address_chain == ["c:main-a:test1", "c:secondary-a:test2"]
        test2_record.remove(payload)

    courier = Courier(dead_letter_channel=dead_letter_channel, instrumentation=TestIns())

    dead_addrs = {"test1", "test3", "test-meta"}
    dead_record = {10, 30}

    def normal_dead_check(parcel: Parcel):
        dead_addrs.remove(parcel.tag)
        assert parcel.receipt.delivery_status == DeliveryStatus.DEAD
        assert len(parcel.receipt.address_chain) >= 2
        dead_record.remove(parcel.payload)
        assert any("c:dead" in addr for addr in parcel.receipt.address_chain)

    def type_dead_check(parcel: Parcel, excs: ExceptionGroup | None, deason: DEAD_REASON):
        dead_addrs.remove(parcel.tag)
        logger.info(f"parcel dead because: {parcel.receipt.dead_reason}")
        assert parcel.receipt.delivery_status == DeliveryStatus.DEAD
        assert parcel.receipt.dead_reason == deason
        assert excs
        assert any(isinstance(e, TypeMisMatch) for e in excs.exceptions)
        assert "TypeMisMatch(" in deason
        assert "value='err-type'" in deason
        assert "type=int" in deason

    @courier.receive_from_dead_letter
    async def dead_letter_comsumer(parcel: Parcel, exc: ExceptionGroup | None, exception, dead_reason, ds: DEAD_REASON):
        logger.info(f"!!!!!!!!!!dead_letter_comsumer: {parcel=}, {exc=}, {dead_reason=}")
        assert isinstance(parcel, Parcel)
        assert exception is exc
        assert dead_reason == ds
        if parcel.payload == "meta":
            type_dead_check(parcel, exc, ds)
        else:
            normal_dead_check(parcel)

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

    async def meta_producer(addr: Address, payload: str, metadata: Metadata):
        parcel = Parcel(addr, payload, metadata)
        r = await post_to_courier(parcel)
        logger.info(f"receipt: {r() if r else r}")

    meta_addr = {"meta"}

    @Courier.receive_from("test-meta")
    async def test_meta_consumer(
        payload: str,
        key0: Annotated[str, MetaFetch()],
        key1=MetaFetch(),
        key2: int = MetaFetch("key2_"),
        key_miss=MetaFetch("key-miss", default="miss"),
    ):
        assert payload == "meta"
        assert key0 == "v0"
        assert key1 is True
        assert key2 == 2
        assert key_miss == "miss"
        meta_addr.discard(payload)

    async with anyio.create_task_group() as tg:
        tg.start_soon(courier.run)
        tg.start_soon(producer, "test1")
        tg.start_soon(meta_producer, "test-meta", "meta", {"key0": "v0", "key1": True, "key2_": 2})
        tg.start_soon(meta_producer, "test-meta", "meta", {"key0": "v0", "key1": True, "key2_": "err-type"})
        await anyio.sleep(10)
        assert not dead_addrs
        assert not dead_record
        assert not meta_addr
        tg.cancel_scope.cancel()
