import nonebot
from pydantic import BaseSettings


class PlugConfig(BaseSettings):

    bison_config_path: str = ""
    bison_use_pic: bool = False
    bison_init_filter: bool = True
    bison_use_queue: bool = True
    bison_outer_url: str = "http://localhost:8080/bison/"
    bison_filter_log: bool = False
    bison_to_me: bool = True
    bison_skip_browser_check: bool = False
    bison_use_pic_merge: int = 0  # 多图片时启用图片合并转发（仅限群）,当bison_use_queue为False时该配置不会生效
    # 0：不启用；1：首条消息单独发送，剩余照片合并转发；2以及以上：所有消息全部合并转发
    bison_resend_times: int = 0

    class Config:
        extra = "ignore"


global_config = nonebot.get_driver().config
plugin_config = PlugConfig(**global_config.dict())
