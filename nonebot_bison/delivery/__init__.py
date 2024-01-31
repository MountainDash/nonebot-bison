import asyncio

from nonebot import logger, get_driver

from nonebot_bison.types import Parcel

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


def _create_default_conveyor():
    """创建默认的传送带"""
    logger.info("create default conveyor")

    for _, member in DefaultConveyor.__members__.items():
        conveyor = Conveyor(member, max_buffer=10)
        logger.success(f"created default conveyor |{member}|")
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
    _create_default_conveyor()

    async def _create_default_conveyor_dispatch_tasks(conveyor_name):
        logger.success(f"start dispatch task for conveyor {conveyor_name}")
        logger.info(f"conveyor {conveyor_name} statistics: {__default_conveyor_record[conveyor_name].statistics()}")
        async with __default_conveyor_record[conveyor_name].get_forever() as channel:
            logger.info(f"conveyor {conveyor_name} statistics: {__default_conveyor_record[conveyor_name].statistics()}")
            async for parcel in channel:
                logger.debug(f"dispatch parcel to conveyor {conveyor_name}")
                await _parcel_dispatch(parcel)

    # async with anyio.create_task_group() as tg:
    #     for conveyor_name in __default_conveyor_record:
    #         await tg.spawn(_create_default_conveyor_dispatch_tasks, conveyor_name)
    for conveyor_name in __default_conveyor_record:
        asyncio.create_task(_create_default_conveyor_dispatch_tasks(conveyor_name))

    logger.success("delivery init done")


@get_driver().on_shutdown
async def _shutdown_delivery():
    logger.info("shutdown delivery")
    for conveyor in __default_conveyor_record.values():
        logger.info(conveyor.statistics())
        await conveyor.ashutdown()
        logger.info(conveyor.statistics())
    logger.success("delivery shutdown done")


__all__ = [
    "init_delivery",
]
