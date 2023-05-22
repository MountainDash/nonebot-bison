import time
import typing

import pytest
import respx
from httpx import AsyncClient, Response
from nonebug.app import App

from .utils import get_json

if typing.TYPE_CHECKING:
    from nonebot_bison.platform.ncm import NcmArtist


@pytest.fixture
def ncm_artist(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import ProcessContext

    return platform_manager["ncm-artist"](ProcessContext(), AsyncClient())


@pytest.fixture(scope="module")
def ncm_artist_raw():
    return get_json("ncm_siren.json")


@pytest.fixture(scope="module")
def ncm_artist_0(ncm_artist_raw):
    return {**ncm_artist_raw, "hotAlbums": ncm_artist_raw["hotAlbums"][1:]}


@pytest.fixture(scope="module")
def ncm_artist_1(ncm_artist_raw: dict):
    res = ncm_artist_raw.copy()
    res["hotAlbums"] = ncm_artist_raw["hotAlbums"][:]
    res["hotAlbums"][0]["publishTime"] = int(time.time() * 1000)
    return res


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(ncm_artist, ncm_artist_0, ncm_artist_1, dummy_user_subinfo):
    from nonebot_bison.post.utils import timestamp_to_str

    ncm_router = respx.get("https://music.163.com/api/artist/albums/32540734")
    ncm_router.mock(return_value=Response(200, json=ncm_artist_0))
    target = "32540734"
    res = await ncm_artist.fetch_new_post(target, [dummy_user_subinfo])
    assert ncm_router.called
    assert len(res) == 0
    ncm_router.mock(return_value=Response(200, json=ncm_artist_1))
    res2 = await ncm_artist.fetch_new_post(target, [dummy_user_subinfo])
    post = res2[0][1][0]
    assert post.target_type == "ncm-artist"
    assert post.text == "新专辑发布：Y1K"
    assert post.url == "https://music.163.com/#/album?id=131074504"
    assert post.card.dict() == {
        "type": "live",
        "header": {
            "face": "https://p1.music.126.net/P4AH7I3NDtSq4FX07e5Lwg==/109951164481881457.jpg",
            "name": "塞壬唱片-MSR",
            "desc": timestamp_to_str(
                ncm_artist_1["hotAlbums"][0]["publishTime"] // 1000
            ),
            "platform": "网易云-歌手",
        },
        "content": {
            "text": "新专辑发布：<br>Y1K - Single",
            "cover": "https://p1.music.126.net/RUCLCpxDdPB4H4R9R10UPA==/109951166229373550.jpg",
        },
        "extra_head": None,
    }


async def test_parse_target(ncm_artist: "NcmArtist"):
    from nonebot_bison.platform.platform import Platform

    res = await ncm_artist.parse_target("32540734")
    assert res == "32540734"
    res = await ncm_artist.parse_target("https://music.163.com/#/artist?id=32540734")
    assert res == "32540734"
    res = await ncm_artist.parse_target("music.163.com/#/artist?id=32540734")
    assert res == "32540734"
    with pytest.raises(Platform.ParseTargetException):
        await ncm_artist.parse_target("music.163.com/#/rad?id=32540734")
