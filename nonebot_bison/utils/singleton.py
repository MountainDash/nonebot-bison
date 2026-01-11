from typing import Any, ClassVar


class Singleton(type):
    _instances: ClassVar[dict[Any, Any]] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
