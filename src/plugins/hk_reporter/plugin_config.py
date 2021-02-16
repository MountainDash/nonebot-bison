from pydantic import BaseSettings
import nonebot

class PlugConfig(BaseSettings):

    hk_reporter_config_path: str = ""
    hk_reporter_use_pic: bool = False
    hk_reporter_use_local: bool = False

    class Config:
        extra = 'ignore'

global_config = nonebot.get_driver().config
plugin_config = PlugConfig(**global_config.dict())
