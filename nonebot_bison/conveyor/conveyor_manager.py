import asyncio
import inspect
from collections.abc import Callable
from typing import TypeVar, get_origin

from nonebot import logger, get_driver
from anyio import create_memory_object_stream

T = TypeVar("T")


class ConveyorManager:
    processor_store: dict[tuple, Callable[[T, ...], ...]] = {}
    send_stream, receive_stream = create_memory_object_stream[tuple]()

    def register_parcel_processor(self, processor: Callable) -> Callable:
        """使用反射获取参数类型"""
        sig = inspect.signature(processor)
        params = sig.parameters
        param_types = (params[param].annotation for param in params)
        self.processor_store[tuple(param_types)] = processor

        def wrapper(*args, **kwargs):
            return processor(*args, **kwargs)

        return wrapper

    def find_processor(self, types: tuple) -> Callable:
        """查找符合参数类型的处理器，遵守里氏替换原则"""
        for k, v in self.processor_store.items():
            if len(k) != len(types):
                continue
            for i in range(len(k)):
                type_a = get_origin(types[i]) if get_origin(types[i]) else types[i]
                type_b = get_origin(k[i]) if get_origin(k[i]) else k[i]
                if type_a != type_b and not issubclass(type_a, type_b):
                    break
            else:
                return v

        logger.error(f"no processor found for {types}")
        raise ValueError(f"no processor found for {types}")

    async def entry(self, *args) -> None:
        """发送到传送带并直接返回"""
        await self.send_stream.send(args)

    async def start_loop(self):
        async for parcel in self.receive_stream:
            func = self.find_processor(tuple(map(type, parcel)))
            if inspect.iscoroutinefunction(func):
                await func(*parcel)
            else:
                func(*parcel)


conveyor_manager = ConveyorManager()

driver = get_driver()


@driver.on_startup
async def start_parcel_process_loop():
    asyncio.create_task(conveyor_manager.start_loop())
    logger.debug("parcel process loop started")
