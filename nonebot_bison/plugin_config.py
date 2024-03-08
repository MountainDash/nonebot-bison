import nonebot
from yarl import URL
from nonebot import get_plugin_config
from pydantic import Field, BaseModel

global_config = nonebot.get_driver().config
PlatformName = str
ThemeName = str


class PlugConfig(BaseModel):
    bison_config_path: str = ""
    bison_use_pic: bool = Field(
        default=False,
        description="发送消息时将所有文本转换为图片，防止风控，仅需要推送文转图可以为 platform 指定 theme",
    )
    bison_theme_use_browser: bool = Field(default=False, description="是否允许主题使用浏览器")
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
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
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
