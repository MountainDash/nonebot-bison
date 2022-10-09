import base64
import hashlib
import platform
from io import UnsupportedOperation
from pathlib import Path

import pytest
import respx
from httpx import Response
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebug.app import App


@pytest.fixture
def ms_list():
    msg_segments: list[MessageSegment] = []
    msg_segments.append(MessageSegment.text("【Zc】每早合约日替攻略！"))
    msg_segments.append(
        MessageSegment.image(
            file="http://i0.hdslb.com/bfs/live/new_room_cover/cf7d4d3b2f336c6dba299644c3af952c5db82612.jpg",
            cache=0,
        )
    )
    msg_segments.append(MessageSegment.text("来源: Bilibili直播 魔法Zc目录"))
    msg_segments.append(MessageSegment.text("详情: https://live.bilibili.com/3044248"))

    return msg_segments


@pytest.fixture
def expected_md():
    return "【Zc】每早合约日替攻略！<br>![Image](http://i0.hdslb.com/bfs/live/new_room_cover/cf7d4d3b2f336c6dba299644c3af952c5db82612.jpg)\n来源: Bilibili直播 魔法Zc目录<br>详情: https://live.bilibili.com/3044248<br>"


def test_gene_md(app: App, expected_md, ms_list):
    from nonebot_bison.post.custom_post import CustomPost

    cp = CustomPost(message_segments=ms_list)
    cp_md = cp._generate_md()
    assert cp_md == expected_md


@respx.mock
@pytest.mark.asyncio
async def test_gene_pic(app: App, ms_list, expected_md):
    from nonebot_bison.post.custom_post import CustomPost

    pic_router = respx.get(
        "http://i0.hdslb.com/bfs/live/new_room_cover/cf7d4d3b2f336c6dba299644c3af952c5db82612.jpg"
    )

    pic_path = Path(__file__).parent / "platforms" / "static" / "custom_post_pic.jpg"
    with open(pic_path, mode="rb") as f:
        mock_pic = f.read()

    pic_router.mock(return_value=Response(200, stream=mock_pic))

    cp = CustomPost(message_segments=ms_list)
    cp_pic_msg_md: str = cp._generate_md()

    assert cp_pic_msg_md == expected_md
