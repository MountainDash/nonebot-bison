import weakref
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .conveyor import Conveyor


class ConveyorMeta(type):
    _conveyor_record: dict[str, weakref.ref["Conveyor"]] = {}

    def __call__(cls, *args, **kwargs) -> "Conveyor":
        instance = super().__call__(*args, **kwargs)
        cls._conveyor_record[instance.name] = weakref.ref(instance)
        return instance

    @classmethod
    def get_conveyor_ref(cls, name: str) -> weakref.ref["Conveyor"] | None:
        """获取传送带的弱引用"""
        return cls._conveyor_record.get(name)
