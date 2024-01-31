from enum import auto
from functools import wraps
from typing import TYPE_CHECKING
from collections.abc import Callable, Coroutine

from strenum import StrEnum

if TYPE_CHECKING:
    from nonebot_bison.types import Parcel

CONVEYOR_DISPATCH_RECORD: dict[str, dict[str, Callable[["Parcel"], Coroutine[None, None, None]]]] = {}
"""记录传送带的分发函数:

{
    <conveyor_name>: {
        <parcel_label>: <dispatch_function>,
        ...
    }
}
"""


class DefaultConveyor(StrEnum):
    """默认传送带名称"""

    RENDER = auto()
    """渲染传送带"""
    SEND = auto()
    """发送传送带"""


def conveyor_dispatch(conveyor_name: str, parcel_label: str):
    """注册分发函数"""

    def decorator(func: Callable[["Parcel"], Coroutine[None, None, None]]):
        @wraps(func)
        async def wrapper(parcel: "Parcel") -> None:
            return await func(parcel)

        if conveyor_name not in CONVEYOR_DISPATCH_RECORD:
            CONVEYOR_DISPATCH_RECORD[conveyor_name] = {}

        CONVEYOR_DISPATCH_RECORD[conveyor_name][parcel_label] = wrapper
        return wrapper

    return decorator
