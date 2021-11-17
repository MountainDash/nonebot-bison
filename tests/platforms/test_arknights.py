import pytest
import typing
import respx
from httpx import Response
import feedparser

if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_bison

from .utils import get_json, get_file

@pytest.fixture
def arknights(plugin_module: 'nonebot_bison'):
    return plugin_module.platform.platform_manager['arknights']

@pytest.fixture(scope='module')
def arknights_list_0():
    return get_json('arknights_list_0.json')

@pytest.fixture(scope='module')
def arknights_list_1():
    return get_json('arknights_list_1.json')

@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(arknights, dummy_user_subinfo, arknights_list_0, arknights_list_1):
    ak_list_router = respx.get("https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/announcement.meta.json")
    detail_router = respx.get("https://ak-fs.hypergryph.com/announce/IOS/announcement/675.html")
    version_router = respx.get('https://ak-conf.hypergryph.com/config/prod/official/IOS/version')
    preannouncement_router = respx.get('https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json')
    ak_list_router.mock(return_value=Response(200, json=arknights_list_0))
    detail_router.mock(return_value=Response(200, text=get_file('arknights-detail-675.html')))
    version_router.mock(return_value=Response(200, json=get_json('arknights-version-0.json')))
    preannouncement_router.mock(return_value=Response(200, json=get_json('arknights-pre-0.json')))
    target = ''
    res = await arknights.fetch_new_post(target, [dummy_user_subinfo])
    assert(ak_list_router.called)
    assert(len(res) == 0)
    assert(not detail_router.called)
    mock_data = arknights_list_1
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res3 = await arknights.fetch_new_post(target, [dummy_user_subinfo])
    assert(len(res3[0][1]) == 1)
    assert(detail_router.called)
    post = res3[0][1][0]
    assert(post.target_type == 'arknights')
    assert(post.text == '')
    assert(post.url == '')
    assert(post.target_name == '明日方舟游戏内公告')
    assert(len(post.pics) == 1)
    assert(post.pics == ['https://ak-fs.hypergryph.com/announce/images/20210623/e6f49aeb9547a2278678368a43b95b07.jpg'])
    r = await post.generate_messages()
