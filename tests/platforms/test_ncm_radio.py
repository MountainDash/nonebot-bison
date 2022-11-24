import time
import typing

import pytest
import respx
from httpx import AsyncClient, Response
from nonebug.app import App

from .utils import get_json

if typing.TYPE_CHECKING:
    from nonebot_bison.platform.ncm import NcmRadio


@pytest.fixture
def ncm_radio(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import ProcessContext

    return platform_manager["ncm-radio"](ProcessContext(), AsyncClient())


@pytest.fixture(scope="module")
def ncm_radio_raw():
    return get_json("ncm_radio_ark.json")


@pytest.fixture(scope="module")
def ncm_radio_0(ncm_radio_raw):
    return {**ncm_radio_raw, "programs": ncm_radio_raw["programs"][1:]}


@pytest.fixture(scope="module")
def ncm_radio_1(ncm_radio_raw: dict):
    res = ncm_radio_raw.copy()
    res["programs"] = ncm_radio_raw["programs"][:]
    res["programs"][0]["createTime"] = int(time.time() * 1000)
    return res


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(ncm_radio, ncm_radio_0, ncm_radio_1, dummy_user_subinfo):
    ncm_router = respx.post("http://music.163.com/api/dj/program/byradio")
    ncm_router.mock(return_value=Response(200, json=ncm_radio_0))
    target = "793745436"
    res = await ncm_radio.fetch_new_post(target, [dummy_user_subinfo])
    assert ncm_router.called
    assert len(res) == 0
    ncm_router.mock(return_value=Response(200, json=ncm_radio_1))
    res2 = await ncm_radio.fetch_new_post(target, [dummy_user_subinfo])
    post = res2[0][1][0]
    print(post)
    assert post.target_type == "ncm-radio"
    assert post.text == "网易云电台更新：「松烟行动」灰齐山麓"
    assert post.url == "https://music.163.com/#/program/2494997688"
    assert post.pics == [
        "http://p1.music.126.net/H5em5xUNIYXcjJhOmeaSqQ==/109951166647436789.jpg"
    ]
    assert post.target_name == "《明日方舟》游戏原声OST"


async def test_parse_target(ncm_radio: "NcmRadio"):
    res = await ncm_radio.parse_target("https://music.163.com/#/djradio?id=793745436")
    assert res == "793745436"
    res = await ncm_radio.parse_target("music.163.com/#/djradio?id=793745436")
    assert res == "793745436"
    res = await ncm_radio.parse_target("793745436")
    assert res == "793745436"
    with pytest.raises(ncm_radio.ParseTargetException):
        await ncm_radio.parse_target("music.163.com/#/alm?id=793745436")
