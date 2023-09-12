from abc import ABC, abstractmethod

from pydantic import BaseModel
from nonebot_plugin_saa import MessageSegmentFactory


class BaseStem(ABC, BaseModel):
    @abstractmethod
    async def render(self) -> list[MessageSegmentFactory] | MessageSegmentFactory:
        ...

    def __str__(self):
        return f"<{self.__class__.__name__} {self.schema_json(ensure_ascii=False)}>"


class ThemeMetadata(BaseModel, frozen=True):
    theme: str
    stem: type[BaseStem]
    """主题的数据枝干，用于检查数据是否符合主题的数据架构"""

    def __str__(self):
        return f"<ThemeMetadata theme={self.theme} stem={self.stem!s}>"
