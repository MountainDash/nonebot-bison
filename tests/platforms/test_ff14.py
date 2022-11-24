import pytest
import respx
from httpx import AsyncClient, Response
from nonebug.app import App

from .utils import get_json


@pytest.fixture
def ff14(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import ProcessContext

    return platform_manager["ff14"](ProcessContext(), AsyncClient())


@pytest.fixture(scope="module")
def ff14_newdata_json_0():
    return get_json("ff14-newdata-0.json")


@pytest.fixture(scope="module")
def ff14_newdata_json_1():
    return get_json("ff14-newdata-1.json")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(
    ff14, dummy_user_subinfo, ff14_newdata_json_0, ff14_newdata_json_1
):
    newdata = respx.get(
        "https://ff.web.sdo.com/inc/newdata.ashx?url=List?gameCode=ff&category=5309,5310,5311,5312,5313&pageIndex=0&pageSize=5"
    )
    newdata.mock(return_value=Response(200, json=ff14_newdata_json_0))
    target = ""
    res = await ff14.fetch_new_post(target, [dummy_user_subinfo])
    assert newdata.called
    assert len(res) == 0
    newdata.mock(return_value=Response(200, json=ff14_newdata_json_1))
    res = await ff14.fetch_new_post(target, [dummy_user_subinfo])
    assert newdata.called
    post = res[0][1][0]
    assert post.target_type == "ff14"
    assert post.text == "最终幻想XIV 银质坠饰 ＜友谊永存＞预售开启！\n最终幻想XIV 银质坠饰 ＜友谊永存＞现已开启预售！"
    assert post.url == "https://ff.web.sdo.com/web8/index.html#/newstab/newscont/336870"
    assert post.target_name == "最终幻想XIV官方公告"
