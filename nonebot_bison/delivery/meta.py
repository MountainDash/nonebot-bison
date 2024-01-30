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
    def get_conveyor(cls, name: str) -> "Conveyor | None":
        if conveyor_ref := cls._conveyor_record.get(name):
            if c := conveyor_ref():
                return c
            else:
                del cls._conveyor_record[name]
                return None

        return None
