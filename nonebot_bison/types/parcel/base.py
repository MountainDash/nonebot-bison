from dataclasses import dataclass

from strenum import StrEnum


class ParcelLabel(StrEnum):
    """包裹的标签，用于标识包裹的类型"""

    POST = "POST"
    """Post包裹"""
    MESSAGE = "MESSAGE"
    """Message包裹"""


@dataclass(kw_only=True)
class ParcelHeader:
    """包裹头部"""

    label: str | None = None
    """包裹的标签，用于标识包裹的类型"""
    conveyor: str | None = None
    """包裹的传送带, 用于标识包裹的传送带"""


@dataclass
class ParcelPayload:
    """包裹内容"""

    pass


@dataclass
class Parcel:
    """包裹"""

    header: ParcelHeader
    payload: ParcelPayload
