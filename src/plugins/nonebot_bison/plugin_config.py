from pydantic import BaseSettings

import warnings
import nonebot

class PlugConfig(BaseSettings):

    bison_config_path: str = ""
    bison_use_pic: bool = False
    bison_use_local: bool = False
    bison_browser: str = ''
    bison_init_filter: bool = True
    bison_use_queue: bool = True

    class Config:
        extra = 'ignore'

global_config = nonebot.get_driver().config
plugin_config = PlugConfig(**global_config.dict())
if plugin_config.bison_use_local:
    warnings.warn('BISON_USE_LOCAL is deprecated, please use BISON_BROWSER')
