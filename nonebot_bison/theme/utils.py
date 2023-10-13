from nonebot import require

from .types import ThemeRenderUnsupportError


def check_htmlrender_plugin_enable():
    try:
        require("nonebot_plugin_htmlrender")
    except RuntimeError as e:
        if "Cannot load plugin" in str(e):
            raise ThemeRenderUnsupportError("需要安装`nonebot_plugin_htmlrender`插件")
        else:
            raise e
