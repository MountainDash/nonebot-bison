import nonebot
from pydantic import BaseSettings

global_config = nonebot.get_driver().config


class PlugConfig(BaseSettings):
    bison_config_path: str = ""
    bison_use_pic: bool = False
    bison_init_filter: bool = True
    bison_use_queue: bool = True
    bison_outer_url: str = ""
    bison_filter_log: bool = False
    bison_to_me: bool = True
    bison_skip_browser_check: bool = False
    bison_use_pic_merge: int = 0  # 多图片时启用图片合并转发（仅限群）
    # 0：不启用；1：首条消息单独发送，剩余照片合并转发；2以及以上：所有消息全部合并转发
    bison_resend_times: int = 0
    bison_proxy: str | None
    bison_ua: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
    )
    bison_show_network_warning: bool = True

    @property
    def outer_url(self) -> str:
        return self.bison_outer_url or f"http://localhost:{global_config.port}/bison/"

    class Config:
        extra = "ignore"


plugin_config = PlugConfig(**global_config.dict())
