import pytest
import typing

if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_hk_reporter

@pytest.fixture
def config(plugin_module):
    plugin_module.config.start_up()
    return plugin_module.config.Config()

def test_create_and_get(config: 'nonebot_hk_reporter.config.Config', plugin_module: 'nonebot_hk_reporter'):
    config.add_subscribe(
            user='123',
            user_type='group',
            target='weibo_id',
            target_name='weibo_name',
            target_type='weibo',
            cats=[],
            tags=[])
    confs = config.list_subscribe('123', 'group')
    assert(len(confs) == 1)
    assert(config.target_user_cache['weibo']['weibo_id'] == \
            [plugin_module.types.User('123', 'group')])
