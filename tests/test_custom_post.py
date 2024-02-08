from pathlib import Path

import respx
import pytest
from httpx import Response
from nonebug.app import App


@pytest.fixture()
def ms_list():
    from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

    msg_segments: list[MessageSegmentFactory] = []
    msg_segments.append(Text("【Zc】每早合约日替攻略！"))
    msg_segments.append(
        Image(
            image="http://i0.hdslb.com/bfs/live/new_room_cover/cf7d4d3b2f336c6dba299644c3af952c5db82612.jpg",
        )
    )
    msg_segments.append(Text("来源: Bilibili直播 魔法Zc目录"))
    msg_segments.append(Text("详情: https://live.bilibili.com/3044248"))

    return msg_segments


@pytest.fixture()
def expected_md():
    return (
        "【Zc】每早合约日替攻略！<br>![Image](http://i0.hdslb.com/bfs/live/new_room_cover/cf7d4d3b2f336c6dba299644c3af952c5db82612.jpg)\n来源:"
        " Bilibili直播 魔法Zc目录<br>详情: https://live.bilibili.com/3044248<br>"
    )


def test_gene_md(app: App, expected_md, ms_list):
    from nonebot_bison.post.custom_post import CustomPost

    cp = CustomPost(ms_factories=ms_list)
    cp_md = cp._generate_md()
    assert cp_md == expected_md


@respx.mock
@pytest.mark.asyncio
async def test_gene_pic(app: App, ms_list, expected_md):
    from nonebot_bison.post.custom_post import CustomPost

    pic_router = respx.get("http://i0.hdslb.com/bfs/live/new_room_cover/cf7d4d3b2f336c6dba299644c3af952c5db82612.jpg")

    pic_path = Path(__file__).parent / "platforms" / "static" / "custom_post_pic.jpg"
    with open(pic_path, mode="rb") as f:
        mock_pic = f.read()

    pic_router.mock(return_value=Response(200, stream=mock_pic))  # type: ignore

    cp = CustomPost(ms_factories=ms_list)
    cp_pic_msg_md: str = cp._generate_md()

    assert cp_pic_msg_md == expected_md
