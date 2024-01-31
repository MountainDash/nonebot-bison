from enum import Enum
from functools import wraps
from typing import TYPE_CHECKING
from collections.abc import Callable, Coroutine

if TYPE_CHECKING:
    from .model import Parcel


CONVEYOR_DISPATCH_RECORD: dict[str, dict[str, Callable[[Parcel], Coroutine[None, None, None]]]] = {}
"""记录传送带的分发函数:

{
    <conveyor_name>: {
        <parcel_label>: <dispatch_function>,
        ...
    }
}
"""


class DefaultConveyor(Enum, str):
    """默认传送带名称"""

    MAIN = "main"


def conveyor_dispatch(conveyor_name: str, parcel_label: str):
    """注册分发函数"""

    def decorator(func: Callable[[Parcel], Coroutine[None, None, None]]):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        if conveyor_name not in CONVEYOR_DISPATCH_RECORD:
            CONVEYOR_DISPATCH_RECORD[conveyor_name] = {}

        CONVEYOR_DISPATCH_RECORD[conveyor_name][parcel_label] = wrapper
        return wrapper

    return decorator
