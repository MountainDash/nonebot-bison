from typing import Literal, Type


class SchedulerConfig:

    schedule_type: Literal["date", "interval", "cron"]
    schedule_setting: dict
    registry: dict[str, Type["SchedulerConfig"]] = {}
    name: str

    def __init_subclass__(cls, *, name, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.registry[name] = cls
        cls.name = name

    def __str__(self):
        return f"[{self.name}]-{self.name}-{self.schedule_setting}"
