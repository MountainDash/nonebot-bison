from nonebot import logger

from .model import Parcel
from .conveyor import Conveyor
from .registry import MAIN_CONVEYOR, CONVEYOR_DISPATCH_RECORD

_conveyor_record: dict[str, Conveyor] = {}


async def create_default_conveyor():
    """创建默认的传送带"""
    logger.info("create default conveyor")
    conveyor = Conveyor(MAIN_CONVEYOR, max_buffer=10)
    _conveyor_record[MAIN_CONVEYOR] = conveyor


async def parcel_dispatch(parcel: Parcel):
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
    await create_default_conveyor()

    async for parcel in _conveyor_record[MAIN_CONVEYOR].get_forever():
        await parcel_dispatch(parcel)


__all__ = [
    "init_delivery",
]
