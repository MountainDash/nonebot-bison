from pydantic import BaseSettings

class PlugConfig(BaseSettings):

    hk_reporter_config_path: str = ""

    class Config:
        extra = 'ignore'
