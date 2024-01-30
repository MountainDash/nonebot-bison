from pydantic import BaseModel

from .registry import MAIN_CONVEYOR


class ParcelHeader(BaseModel):
    """包裹头部"""

    label: str
    """包裹的标签，用于标识包裹的类型"""
    conveyor: str = MAIN_CONVEYOR
    """包裹的传送带, 用于标识包裹的传送带, 默认为 MAIN_CONVEYOR"""


class ParcelPayload(BaseModel):
    """包裹内容"""

    pass


class Parcel(BaseModel):
    """包裹"""

    header: ParcelHeader
    payload: ParcelPayload
