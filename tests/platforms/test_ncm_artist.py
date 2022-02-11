import time

import respx
import pytest
from httpx import Response
from nonebug.app import App

from .utils import get_json


@pytest.fixture
def ncm_artist(app: App):
    from nonebot_bison.platform import platform_manager

    return platform_manager["ncm-artist"]


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
