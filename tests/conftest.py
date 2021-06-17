import pytest
import nonebot
import typing

if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_hk_reporter

@pytest.fixture#(scope="module")
def plugin_module(tmpdir):
    nonebot.init(hk_reporter_config_path=str(tmpdir))
    nonebot.load_plugins('src/plugins')
    plugins = nonebot.get_loaded_plugins()
    plugin = list(filter(lambda x: x.name == 'nonebot_hk_reporter', plugins))[0]
    return plugin.module

@pytest.fixture
def dummy_user_subinfo(plugin_module: 'nonebot_hk_reporter'):
    user = plugin_module.types.User('123', 'group')
    return plugin_module.types.UserSubInfo(
            user=user,
            category_getter=lambda _: [],
            tag_getter=lambda _: []
            )

