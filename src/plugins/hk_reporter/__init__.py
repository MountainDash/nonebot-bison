import nonebot
from .plugin_config import PlugConfig
global_config = nonebot.get_driver().config
plugin_config = PlugConfig(**global_config.dict())

from . import config_manager
from . import config
from . import scheduler
from . import send

