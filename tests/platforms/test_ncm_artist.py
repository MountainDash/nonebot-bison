import time
import typing

from httpx import Response
from nonebug.app import App
import pytest
import respx

from .utils import get_json

if typing.TYPE_CHECKING:
    from nonebot_bison.platform.ncm import NcmArtist


@pytest.fixture
def ncm_artist(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    return platform_manager["ncm-artist"](ProcessContext(DefaultClientManager()))


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
    from nonebot_bison.types import SubUnit, Target

    ncm_router = respx.get("https://music.163.com/api/artist/albums/32540734")
    ncm_router.mock(return_value=Response(200, json=ncm_artist_0))
    target = Target("32540734")
    res = await ncm_artist.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert ncm_router.called
    assert len(res) == 0
    ncm_router.mock(return_value=Response(200, json=ncm_artist_1))
    res2 = await ncm_artist.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    post = res2[0][1][0]
    assert post.platform.platform_name == "ncm-artist"
    assert post.content == "新专辑发布：Y1K"
    assert post.url == "https://music.163.com/#/album?id=131074504"


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
