from httpx import Response
from nonebug.app import App
import pytest
import respx

from .utils import get_json


@pytest.fixture
def ff14(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    return platform_manager["ff14"](ProcessContext(DefaultClientManager()))


@pytest.fixture(scope="module")
def ff14_newdata_json_0():
    return get_json("ff14-newdata-0.json")


@pytest.fixture(scope="module")
def ff14_newdata_json_1():
    return get_json("ff14-newdata-1.json")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(ff14, dummy_user_subinfo, ff14_newdata_json_0, ff14_newdata_json_1):
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit, Target

    newdata = respx.get(
        "https://cqnews.web.sdo.com/api/news/newsList?gameCode=ff&CategoryCode=5309,5310,5311,5312,5313&pageIndex=0&pageSize=5"
    )
    newdata.mock(return_value=Response(200, json=ff14_newdata_json_0))
    target = Target("")
    res = await ff14.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert newdata.called
    assert len(res) == 0
    newdata.mock(return_value=Response(200, json=ff14_newdata_json_1))
    res = await ff14.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert newdata.called
    post: Post = res[0][1][0]
    assert post.platform.name == "最终幻想XIV官方公告"
    assert post.title == "最终幻想XIV 银质坠饰 ＜友谊永存＞预售开启！"
    assert post.content == "最终幻想XIV 银质坠饰 ＜友谊永存＞现已开启预售！"
    assert post.url == "https://ff.web.sdo.com/web8/index.html#/newstab/newscont/336870"
    assert post.nickname == "最终幻想XIV官方公告"
