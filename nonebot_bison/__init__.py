from nonebot.plugin import PluginMetadata, require

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_datastore")
require("nonebot_plugin_saa")

import nonebot_plugin_saa

from .plugin_config import PlugConfig, plugin_config
from . import post, send, theme, types, utils, config, platform, bootstrap, scheduler, admin_page, sub_manager

__help__version__ = "0.8.2"
nonebot_plugin_saa.enable_auto_select_bot()

__help__plugin__name__ = "nonebot_bison"
__usage__ = (
    "本bot可以提供b站、微博等社交媒体的消息订阅，详情请查看本bot文档，"
    f"或者{'at本bot' if plugin_config.bison_to_me else '' }发送“添加订阅”订阅第一个帐号，"
    "发送“查询订阅”或“删除订阅”管理订阅"
)

__supported_adapters__ = nonebot_plugin_saa.__plugin_meta__.supported_adapters

__plugin_meta__ = PluginMetadata(
    name="Bison",
    description="通用订阅推送插件",
    usage=__usage__,
    type="application",
    homepage="https://github.com/felinae98/nonebot-bison",
    config=PlugConfig,
    supported_adapters=__supported_adapters__,
    extra={"version": __help__version__, "docs": "https://nonebot-bison.netlify.app/"},
)

__all__ = [
    "admin_page",
    "bootstrap",
    "config",
    "sub_manager",
    "post",
    "scheduler",
    "send",
    "platform",
    "types",
    "utils",
    "theme",
]
