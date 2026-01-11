from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

from httpx import AsyncClient

from nonebot_bison.typing import Target


class ClientManager(ABC):
    @abstractmethod
    async def get_client(self, target: Target | None) -> AsyncClient: ...

    @abstractmethod
    async def get_client_for_static(self) -> AsyncClient: ...

    @abstractmethod
    async def get_query_name_client(self) -> AsyncClient: ...

    @abstractmethod
    async def refresh_client(self): ...

    @abstractmethod
    async def on_init_scheduler(self):
        """在调度器初始化时调用，可用于提前准备Client等操作"""


@dataclass(kw_only=True)
class SiteConfig:
    name: str
    """站点名称, 用于区分不同站点，是唯一标识"""
    schedule_type: Literal["date", "interval", "cron"]
    """调度类型，是apscheduler支持的类型之一"""
    schedule_setting: dict[str, Any]
    """调度配置，一般是 apscheduler 的配置格式"""
    client_mgr: type[ClientManager]
    """用于请求站点的 HTTP 接口，如果没有特殊要求可以使用默认的 DefaultClientManager"""
    require_browser: bool = False

    def __str__(self):
        return f"[{self.name}]-{self.name}-{self.schedule_setting}"
