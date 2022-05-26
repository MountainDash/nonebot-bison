from datetime import datetime

import feedparser
import pytest
import respx
from httpx import Response
from nonebug.app import App
from pytz import timezone

from .utils import get_file, get_json


@pytest.fixture
def bili_live(app: App):
    from nonebot_bison.platform import platform_manager

    return platform_manager["bilibili-live"]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bilibili_live_status(bili_live, dummy_user_subinfo):
    mock_bili_live_status = get_json("bili_live_status.json")

    bili_live_router = respx.get(
        "https://api.bilibili.com/x/space/acc/info?mid=13164144"
    )
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    target = "13164144"
    res = await bili_live.fetch_new_post(target, [dummy_user_subinfo])
    assert bili_live_router.called
    assert len(res) == 0
    mock_bili_live_status["data"]["live_room"]["liveStatus"] = 1
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res2 = await bili_live.fetch_new_post(target, [dummy_user_subinfo])
    post = res2[0][1][0]
    assert post.target_type == "Bilibili直播"
    assert post.text == "【Zc】早朝危机合约！"
    assert post.url == "https://live.bilibili.com/3044248"
    assert post.target_name == "魔法Zc目录"
    assert post.pics == [
        "http://i0.hdslb.com/bfs/live/new_room_cover/cf7d4d3b2f336c6dba299644c3af952c5db82612.jpg"
    ]
    assert post.compress == True
