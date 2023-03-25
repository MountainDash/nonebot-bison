from abc import ABC
from typing import Any

from nonebot.log import logger
from pydantic import BaseModel
from typing_extensions import Self

from ..utils import NBESFParseErr


class NBESFBase(BaseModel, ABC):

    version: int = 0  # 表示nbesf格式版本，有效版本从1开始
    groups: list = list()

    class Config:
        orm_mode = True

    def __init_subclass__(cls, ver: int) -> None:
        cls.version = ver

    @classmethod
    def parse_nbesf(cls, raw_data: Any) -> Self:
        try:
            assert cls.version

            if isinstance(raw_data, str):
                nbesf_data = cls.parse_raw(raw_data)
            else:
                nbesf_data = cls.parse_obj(raw_data)

        except Exception as e:
            logger.error("数据解析失败，该数据格式可能不满足NBESF格式标准！")
            raise NBESFParseErr("数据解析失败") from e
        else:
            return nbesf_data
