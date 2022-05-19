import pytest
import respx
from httpx import Response
from nonebug.app import App

from .utils import get_file, get_json


@pytest.fixture
def mcbbsnews(app: App):
    from nonebot_bison.platform import platform_manager
    
    return platform_manager['mcbbsnews']

@pytest.fixture(scope="module")
def raw_post_list():
    return get_json('mcbbsnews_raw_post_list.json')

@pytest.mark.asyncio
async def test_javanews_parser(mcbbsnews,raw_post_list):
    post = await mcbbsnews.parse(raw_post_list)
    assert post.text==''