from pydantic import BaseSettings

class PlugConfig(BaseSettings):

    hk_reporter_config_path: str = ""
    hk_reporter_use_pic: bool = False
    hk_reporter_use_local: bool = False

    class Config:
        extra = 'ignore'
