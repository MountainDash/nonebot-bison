import pytest
import typing
import respx
from httpx import Response
import feedparser

if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_hk_reporter

from .utils import get_json, get_file

@pytest.fixture
def monster_siren(plugin_module: 'nonebot_hk_reporter'):
    return plugin_module.platform.platform_manager['monster-siren']

@pytest.fixture(scope='module')
def monster_siren_list_0():
    return get_json('monster-siren_list_0.json')

@pytest.fixture(scope='module')
def monster_siren_list_1():
    return get_json('monster-siren_list_1.json')

@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(monster_siren, dummy_user_subinfo, monster_siren_list_0, monster_siren_list_1):
    ak_list_router = respx.get("https://monster-siren.hypergryph.com/api/news")
    ak_list_router.mock(return_value=Response(200, json=monster_siren_list_0))
    target = ''
    res = await monster_siren.fetch_new_post(target, [dummy_user_subinfo])
    assert(ak_list_router.called)
    assert(len(res) == 0)
    mock_data = monster_siren_list_1
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res3 = await monster_siren.fetch_new_post(target, [dummy_user_subinfo])
    assert(len(res3[0][1]) == 1)
    post = res3[0][1][0]
    assert(post.target_type == 'monster-siren')
    assert(post.text == '#D.D.D.PHOTO')
    assert(post.url == 'https://monster-siren.hypergryph.com/info/241303')
    assert(post.target_name == '塞壬唱片新闻')
    assert(len(post.pics) == 0)
