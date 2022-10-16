from typing import Literal, Type

from httpx import AsyncClient

from ..types import Target
from .http import http_client


class SchedulerConfig:

    schedule_type: Literal["date", "interval", "cron"]
    schedule_setting: dict
    name: str

    def __str__(self):
        return f"[{self.name}]-{self.name}-{self.schedule_setting}"

    def __init__(self):
        self.default_http_client = http_client()

    async def get_client(self, target: Target) -> AsyncClient:
        return self.default_http_client

    async def get_query_name_client(self) -> AsyncClient:
        return self.default_http_client


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
