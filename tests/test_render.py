import pytest
import typing

if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_hk_reporter

@pytest.mark.asyncio
@pytest.mark.render
async def test_render(plugin_module: 'nonebot_hk_reporter'):
    render = plugin_module.utils.Render()
    res = await render.text_to_pic('a\nbbbbbbbbbbbbbbbbbbbbbb\ncd')
    print(res)
