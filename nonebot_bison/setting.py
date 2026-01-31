from nonebot import get_driver, get_plugin_config
from nonebot.compat import PYDANTIC_V2, ConfigDict
from pydantic import BaseModel, Field
from yarl import URL

type PlatformName = str
type ThemeName = str


class BisonConfig(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(populate_by_name=True)
    else:

        class Config:
            allow_population_by_field_name = True

    bison_to_me: bool = True
    bison_show_network_warning: bool = True
    bison_outer_url: str = ""
    bison_config_path: str = ""
    bison_render_post_concurrency: int = 5
    bison_platform_theme: dict[PlatformName, ThemeName] = {}
    bison_use_browser: bool = False
    bison_proxy: str | None = None
    bison_ua: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        description="默认UA",
    )
    bison_filter_on_init: bool = True

    @property
    def outer_url(self) -> URL:
        if self.bison_outer_url:
            return URL(self.bison_outer_url)
        else:
            return URL(f"http://localhost:{get_driver().config.port}/bison/")


plugin_config = get_plugin_config(BisonConfig)
