from pydantic import BaseSettings

class PlugConfig(BaseSettings):

    hk_reporter_config_path: str = ""
    use_pic: bool = False

    class Config:
        extra = 'ignore'
