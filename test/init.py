import typing
if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_hk_reporter
import nonebot

nonebot.init()
plugins = nonebot.load_plugins('src/plugins')
plugin = list(filter(lambda x: x.name == 'nonebot_hk_reporter', plugins))[0]
if typing.TYPE_CHECKING:
    plugin_module : nonebot_hk_reporter = plugin.module
else:
    plugin_module = plugin.module
