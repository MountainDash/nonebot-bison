import pytest
import typing
if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_hk_reporter

@pytest.mark.asyncio
async def test_get_name(plugin_module: 'nonebot_hk_reporter'):
    weibo = plugin_module.platform.platform_manager['weibo']
    name = await weibo.get_account_name('6279793937')
    assert(name == "明日方舟Arknights")
