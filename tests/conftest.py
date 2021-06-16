import pytest
import nonebot

@pytest.fixture#(scope="module")
def plugin_module(tmpdir):
    nonebot.init(hk_reporter_config_path=str(tmpdir))
    nonebot.load_plugins('src/plugins')
    plugins = nonebot.get_loaded_plugins()
    plugin = list(filter(lambda x: x.name == 'nonebot_hk_reporter', plugins))[0]
    return plugin.module
