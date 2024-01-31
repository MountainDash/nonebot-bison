import anyio
from nonebot import logger

from .model import Parcel
from .conveyor import Conveyor
from .registry import CONVEYOR_DISPATCH_RECORD, DefaultConveyor

# Conveyor 里记录的是弱引用，这里记录的是实例
__default_conveyor_record: dict[str, Conveyor] = {}


def get_default_conveyor(conveyor_name: DefaultConveyor) -> Conveyor:
    """获取默认创建的传送带"""
    if conveyor_name not in __default_conveyor_record:
        logger.error(f"conveyor {conveyor_name} not found")
        raise RuntimeError(f"conveyor {conveyor_name} not found")

    return __default_conveyor_record[conveyor_name]


async def _create_default_conveyor():
    """创建默认的传送带"""
    logger.info("create default conveyor")
    # conveyor = Conveyor(DefaultConveyor.MAIN, max_buffer=10)
    # __default_conveyor_record[DefaultConveyor.MAIN] = conveyor

    for _, member in DefaultConveyor.__members__.items():
        conveyor = Conveyor(member, max_buffer=10)
        __default_conveyor_record[member] = conveyor


async def _parcel_dispatch(parcel: Parcel):
    """分发 Parcel"""
    parcel_label = parcel.header.label
    parcel_conveyor = parcel.header.conveyor
    if parcel_conveyor not in CONVEYOR_DISPATCH_RECORD:
        logger.warning(f"parcel need to be dispatched to conveyor {parcel_conveyor}, but not found")
        return

    if parcel_label not in CONVEYOR_DISPATCH_RECORD[parcel_conveyor]:
        logger.warning(
            f"parcel need to be dispatched to conveyor {parcel_conveyor} with label {parcel_label}, but not found"
        )
        return
    dispatch_func = CONVEYOR_DISPATCH_RECORD[parcel_conveyor][parcel_label]

    await dispatch_func(parcel)


async def init_delivery():
    logger.info("init delivery")
    await _create_default_conveyor()

    async def _create_default_conveyor_dispatch_tasks(conveyor_name):
        async for parcel in __default_conveyor_record[conveyor_name].get_forever():
            await _parcel_dispatch(parcel)

    async with anyio.create_task_group() as tg:
        for conveyor_name in __default_conveyor_record:
            tg.start_soon(_create_default_conveyor_dispatch_tasks, conveyor_name)


__all__ = [
    "init_delivery",
]
