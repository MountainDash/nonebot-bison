from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import anyio

from bison_core.site import SiteConfig

if TYPE_CHECKING:
    from .scheduler import Scheduler

type SiteName = str


@dataclass
class Schedulers:
    schedulers: dict[SiteName, Scheduler] = field(default_factory=dict)

    def __getitem__(self, key: str | SiteConfig, /) -> Scheduler:
        match key:
            case str():
                return self.schedulers[key]
            case SiteConfig():
                return self.schedulers[key.name]
            case _:
                raise TypeError(f"Unsupport SchedulerDict key type: {type(key)}")

    def __setitem__(self, key: str | SiteConfig, value: Scheduler, /):
        match key:
            case str():
                self.schedulers[key] = value
            case SiteConfig():
                self.schedulers[key.name] = value
            case _:
                raise TypeError(f"Unsupport SchedulerDict key type: {type(key)}")

    def __contains__(self, key: str | SiteConfig) -> bool:
        match key:
            case str():
                return key in self.schedulers
            case SiteConfig():
                return key.name in self.schedulers
            case _:
                raise TypeError(f"Unsupport SchedulerDict key type: {type(key)}")

    async def on_plugin_init(self):
        async with anyio.create_task_group() as tg:
            for s in self.schedulers.values():
                tg.start_soon(s.client_mgr.on_init_scheduler)
