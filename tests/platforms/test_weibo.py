import pytest
import typing
import respx
from datetime import datetime
from pytz import timezone
from httpx import Response

if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_hk_reporter

from .utils import get_json, get_file

@pytest.fixture
def weibo(plugin_module: 'nonebot_hk_reporter'):
    return plugin_module.platform.platform_manager['weibo']

@pytest.fixture(scope='module')
def weibo_ak_list_1():
    return get_json('weibo_ak_list_1.json')

@pytest.mark.asyncio
async def test_get_name(weibo):
    name = await weibo.get_account_name('6279793937')
    assert(name == "明日方舟Arknights")

@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(weibo, dummy_user_subinfo):
    ak_list_router = respx.get("https://m.weibo.cn/api/container/getIndex?containerid=1076036279793937")
    detail_router = respx.get("https://m.weibo.cn/detail/4649031014551911")
    ak_list_router.mock(return_value=Response(200, json=get_json('weibo_ak_list_0.json')))
    detail_router.mock(return_value=Response(200, text=get_file('weibo_detail_4649031014551911.html')))
    target = '6279793937'
    res = await weibo.fetch_new_post(target, [dummy_user_subinfo])
    assert(ak_list_router.called)
    assert(len(res) == 0)
    assert(not detail_router.called)
    mock_data = get_json('weibo_ak_list_1.json')
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res2 = await weibo.fetch_new_post(target, [dummy_user_subinfo])
    assert(len(res2) == 0)
    mock_data['data']['cards'][1]['mblog']['created_at'] = \
            datetime.now(timezone('Asia/Shanghai')).strftime('%a %b %d %H:%M:%S %z %Y')
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res3 = await weibo.fetch_new_post(target, [dummy_user_subinfo])
    assert(len(res3[0][1]) == 1)
    assert(not detail_router.called)
    post = res3[0][1][0]
    assert(post.target_type == 'weibo')
    assert(post.text == '#明日方舟#\nSideStory「沃伦姆德的薄暮」复刻现已开启！ ')
    assert(post.url == 'https://weibo.com/6279793937/KkBtUx2dv')
    assert(post.target_name == '明日方舟Arknights')
    assert(len(post.pics) == 1)

@pytest.mark.asyncio
async def test_classification(weibo):
    mock_data = get_json('weibo_ak_list_1.json')
    tuwen = mock_data['data']['cards'][1]
    retweet = mock_data['data']['cards'][3]
    video = mock_data['data']['cards'][0]
    assert(weibo.get_category(retweet) == 1)
    assert(weibo.get_category(video) == 2)
    assert(weibo.get_category(tuwen) == 3)

@pytest.mark.asyncio
@respx.mock
async def test_parse_long(weibo):
    detail_router = respx.get("https://m.weibo.cn/detail/4645748019299849")
    detail_router.mock(return_value=Response(200, text=get_file('weibo_detail_4645748019299849.html')))
    raw_post = get_json('weibo_ak_list_1.json')['data']['cards'][0]
    post = await weibo.parse(raw_post)
    assert(not '全文' in post.text)
    assert(detail_router.called)

def text_tag(weibo, weibo_ak_list_1):
    assert(weibo.get_tags(weibo_ak_list_1) == ['明日方舟', '音律联觉'])
