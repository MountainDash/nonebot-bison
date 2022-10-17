from typing import Callable

import pytest
import respx
from httpx import AsyncClient, Response
from nonebug.app import App

from .utils import get_json


@pytest.fixture
def bili_live(app: App, use_title=True):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.plugin_config import plugin_config

    plugin_config.bison_bililive_repond_when_title_update = use_title

    return platform_manager["bilibili-live"](AsyncClient())


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bililive_status_change(bili_live, dummy_user_subinfo):
    mock_bili_live_status = get_json("bili_live_status.json")

    bili_live_router = respx.get(
        "http://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids[]=13164144"
    )
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))

    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))

    target = "13164144"
    res = await bili_live.fetch_new_post(target, [dummy_user_subinfo])
    assert bili_live_router.called
    assert len(res) == 0
    mock_bili_live_status["data"][target]["live_status"] = 1
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res2 = await bili_live.fetch_new_post(target, [dummy_user_subinfo])
    post = res2[0][1][0]
    assert post.target_type == "Bilibili直播"
    assert post.text == "【Zc】从0挑战到15肉鸽！目前10难度"
    assert post.url == "https://live.bilibili.com/3044248"
    assert post.target_name == "魔法Zc目录"
    assert post.pics == [
        "https://i0.hdslb.com/bfs/live-key-frame/keyframe10170435000003044248mwowx0.jpg"
    ]
    assert post.compress == True


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bililive_title_change(bili_live, dummy_user_subinfo):
    mock_bili_live_status = get_json("bili_live_status.json")
    target = "13164144"
    mock_bili_live_status["data"][target]["live_status"] = 1

    bili_live_router = respx.get(
        "http://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids[]=13164144"
    )
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))

    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))

    res = await bili_live.fetch_new_post(target, [dummy_user_subinfo])
    assert bili_live_router.called
    assert len(res) == 0
    mock_bili_live_status["data"][target]["title"] = "【Zc】从0挑战到15肉鸽！目前11难度"
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res2 = await bili_live.fetch_new_post(target, [dummy_user_subinfo])
    post = res2[0][1][0]
    assert post.target_type == "Bilibili直播"
    assert post.text == "【Zc】从0挑战到15肉鸽！目前11难度"
    assert post.url == "https://live.bilibili.com/3044248"
    assert post.target_name == "魔法Zc目录"
    assert post.pics == [
        "https://i0.hdslb.com/bfs/live-key-frame/keyframe10170435000003044248mwowx0.jpg"
    ]
    assert post.compress == True


import functools


@pytest.mark.asyncio
@pytest.mark.parametrize("bili_live", {"use_title": False}, indirect=True)
@respx.mock
async def test_fetch_bililive_disable_title_change(bili_live, dummy_user_subinfo):

    mock_bili_live_status = get_json("bili_live_status.json")
    target = "13164144"
    mock_bili_live_status["data"][target]["live_status"] = 1

    bili_live_router = respx.get(
        "http://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids[]=13164144"
    )
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))

    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))

    res = await bili_live.fetch_new_post(target, [dummy_user_subinfo])
    assert bili_live_router.called
    assert len(res) == 0

    # mock_bili_live_status["data"][target]["title"] = "【Zc】从0挑战到15肉鸽！目前11难度"
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res2 = await bili_live.fetch_new_post(target, [dummy_user_subinfo])
    post = res2[0][1][0]
    assert post.target_type == "Bilibili直播"
    assert post.text == "【Zc】从0挑战到15肉鸽！目前11难度"
    assert post.url == "https://live.bilibili.com/3044248"
    assert post.target_name == "魔法Zc目录"
    assert post.pics == [
        "https://i0.hdslb.com/bfs/live-key-frame/keyframe10170435000003044248mwowx0.jpg"
    ]
    assert post.compress == True
