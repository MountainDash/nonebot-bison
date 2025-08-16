from datetime import timedelta

import nonebot
from nonebot import get_plugin_config
from nonebot.compat import PYDANTIC_V2, ConfigDict
from pydantic import BaseModel, Field
from yarl import URL

global_config = nonebot.get_driver().config
PlatformName = str
ThemeName = str


class MaxConcurrencyConfig(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(populate_by_name=True)
    else:

        class Config:
            allow_population_by_field_name = True

    render_post: int = Field(default=5, description="渲染动态报文的最大并发数")
    send_message: int = Field(default=100, description="消息发送队列的最大缓存大小")
    resend_wait: timedelta = Field(default=timedelta(seconds=1.5), description="消息重试发送前的等待时间")


class PlugConfig(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(populate_by_name=True)
    else:

        class Config:
            allow_population_by_field_name = True

    bison_max_concurrency: MaxConcurrencyConfig = Field(default_factory=MaxConcurrencyConfig)
    bison_config_path: str = ""
    bison_use_pic: bool = Field(
        default=False,
        description="发送消息时将所有文本转换为图片，防止风控，仅需要推送文转图可以为 platform 指定 theme",
    )
    bison_use_browser: bool = Field(
        default=False, description="是否使用环境中的浏览器", alias="bison_theme_use_browser"
    )
    bison_init_filter: bool = True
    bison_use_queue: bool = True
    bison_outer_url: str = ""
    bison_filter_log: bool = False
    bison_to_me: bool = True
    bison_skip_browser_check: bool = False
    bison_use_pic_merge: int = 0  # 多图片时启用图片合并转发（仅限群）
    # 0：不启用；1：首条消息单独发送，剩余照片合并转发；2以及以上：所有消息全部合并转发
    bison_resend_times: int = 0
    bison_proxy: str | None = None
    bison_ua: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        description="默认UA",
    )
    bison_show_network_warning: bool = True
    bison_platform_theme: dict[PlatformName, ThemeName] = {}

    @property
    def outer_url(self) -> URL:
        if self.bison_outer_url:
            return URL(self.bison_outer_url)
        else:
            return URL(f"http://localhost:{global_config.port}/bison/")


plugin_config = get_plugin_config(PlugConfig)
