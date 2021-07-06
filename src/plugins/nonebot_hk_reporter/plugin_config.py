from pydantic import BaseSettings

import warnings
import nonebot

class PlugConfig(BaseSettings):

    hk_reporter_config_path: str = ""
    hk_reporter_use_pic: bool = False
    hk_reporter_use_local: bool = False
    hk_reporter_browser: str = ''
    hk_reporter_init_filter: bool = True

    class Config:
        extra = 'ignore'

global_config = nonebot.get_driver().config
plugin_config = PlugConfig(**global_config.dict())
if plugin_config.hk_reporter_use_local:
    warnings.warn('HK_REPORTER_USE_LOCAL is deprecated, please use HK_REPORTER_BROWSER')
