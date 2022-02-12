import typing

import nonebot
import pytest

if typing.TYPE_CHECKING:
    import sys

    sys.path.append("./src/plugins")
    import nonebot_bison


@pytest.fixture  # (scope="module")
def plugin_module(tmpdir):
    nonebot.init(bison_config_path=str(tmpdir))
    nonebot.load_plugins("src/plugins")
    plugins = nonebot.get_loaded_plugins()
    plugin = list(filter(lambda x: x.name == "nonebot_bison", plugins))[0]
    return plugin.module


@pytest.fixture
def dummy_user_subinfo(plugin_module: "nonebot_bison"):
    user = plugin_module.types.User("123", "group")
    return plugin_module.types.UserSubInfo(
        user=user, category_getter=lambda _: [], tag_getter=lambda _: []
    )
