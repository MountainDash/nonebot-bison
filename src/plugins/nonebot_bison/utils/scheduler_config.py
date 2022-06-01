from typing import Literal, Type


class SchedulerConfig:

    schedule_type: Literal["date", "interval", "cron"]
    schedule_setting: dict
    registry: dict[str, Type["SchedulerConfig"]] = {}

    def __init_subclass__(cls, *, name, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.registry[name] = cls
