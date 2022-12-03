from nonebot.plugin import require

require("nonebot_plugin_datastore")

from . import (
    admin_page,
    bootstrap,
    config,
    config_manager,
    platform,
    post,
    scheduler,
    send,
    types,
    utils,
)
from .plugin_config import plugin_config

__help__version__ = "0.6.3"
__help__plugin__name__ = "nonebot_bison"
__usage__ = f"本bot可以提供b站、微博等社交媒体的消息订阅，详情请查看本bot文档，或者{'at本bot' if plugin_config.bison_to_me else '' }发送“添加订阅”订阅第一个帐号，发送“查询订阅”或“删除订阅”管理订阅"

__all__ = [
    "admin_page",
    "config",
    "config_manager",
    "post",
    "scheduler",
    "send",
    "platform",
    "types",
    "utils",
]
