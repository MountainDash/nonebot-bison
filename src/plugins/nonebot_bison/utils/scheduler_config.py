from typing import Literal, Type


class SchedulerConfig:

    schedule_type: Literal["date", "interval", "cron"]
    schedule_setting: dict
    name: str

    def __str__(self):
        return f"[{self.name}]-{self.name}-{self.schedule_setting}"


def scheduler(
    schedule_type: Literal["date", "interval", "cron"], schedule_setting: dict
) -> Type[SchedulerConfig]:
    return type(
        "AnonymousScheduleConfig",
        (SchedulerConfig,),
        {
            "schedule_type": schedule_type,
            "schedule_setting": schedule_setting,
        },
    )
