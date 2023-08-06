import respx
import pytest
from nonebug.app import App
from httpx import Response, AsyncClient

from .utils import get_file, get_json


@pytest.fixture()
def arknights(app: App):
    from nonebot_bison.utils import ProcessContext
    from nonebot_bison.platform import platform_manager

    return platform_manager["arknights"](ProcessContext(), AsyncClient())


@pytest.fixture(scope="module")
def arknights_list_0():
    return get_json("arknights_list_0.json")


@pytest.fixture(scope="module")
def arknights_list__1():
    return get_json("arknights_list_-1.json")


@pytest.fixture(scope="module")
def arknights_list_1():
    return get_json("arknights_list_1.json")


@pytest.fixture(scope="module")
def monster_siren_list_0():
    return get_json("monster-siren_list_0.json")


@pytest.fixture(scope="module")
def monster_siren_list_1():
    return get_json("monster-siren_list_1.json")


@pytest.mark.asyncio()
@respx.mock
async def test_fetch_new(
    arknights,
    dummy_user_subinfo,
    arknights_list_0,
    arknights_list__1,
    monster_siren_list_0,
    monster_siren_list_1,
):
    from nonebot_bison.types import Target, SubUnit

    ak_list_router = respx.get("https://ak-webview.hypergryph.com/api/game/bulletinList?target=IOS")
    detail_router = respx.get("https://ak-webview.hypergryph.com/api/game/bulletin/5716")
    version_router = respx.get("https://ak-conf.hypergryph.com/config/prod/official/IOS/version")
    preannouncement_router = respx.get(
        "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json"
    )
    monster_siren_router = respx.get("https://monster-siren.hypergryph.com/api/news")
    terra_list = respx.get("https://terra-historicus.hypergryph.com/api/recentUpdate")

    ak_list_router.mock(return_value=Response(200, json=arknights_list__1))
    detail_router.mock(return_value=Response(200, text=get_file("arknights-detail-807")))
    version_router.mock(return_value=Response(200, json=get_json("arknights-version-0.json")))
    preannouncement_router.mock(return_value=Response(200, json=get_json("arknights-pre-0.json")))
    monster_siren_router.mock(return_value=Response(200, json=monster_siren_list_0))
    terra_list.mock(return_value=Response(200, json=get_json("terra-hist-0.json")))
    target = Target("")
    res1 = await arknights.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert ak_list_router.called
    assert len(res1) == 0
    assert not detail_router.called

    mock_data = arknights_list_0
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res2 = await arknights.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res2[0][1]) == 1
    assert detail_router.called
    post2 = res2[0][1][0]
    assert post2.theme == "arknights"
    assert post2.card_data.announce_title == "2023「夏日嘉年华」限时活动即将开启"
    assert post2.card_data.content

    terra_list.mock(return_value=Response(200, json=get_json("terra-hist-1.json")))
    res3 = await arknights.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res3) == 1
    post3 = res3[0][1][0]
    assert post3.platform == "terra-historicus"
    assert post3.text == "123罗德岛！？ - 「掠风」篇"
    assert post3.url == "https://terra-historicus.hypergryph.com/comic/6253/episode/4938"
    assert post3.pics == ["https://web.hycdn.cn/comic/pic/20220507/ab8a2ff408ec7d587775aed70b178ec0.png"]

    new_version = get_json("arknights-version-0.json")
    new_version["clientVersion"] = "2.0.0"
    version_router.mock(return_value=Response(200, json=new_version))
    new_preannouncement = get_json("arknights-pre-0.json")
    new_preannouncement["clientVersion"] = "2.0.0"
    preannouncement_router.mock(return_value=Response(200, json=new_preannouncement))

    res4 = await arknights.fetch_new_post(target, [dummy_user_subinfo])
    assert len(res4) == 1
    post4 = res4[0][1][0]
    assert post4.platform == "arknights"
    assert post4.text == "游戏本体更新（大更新）"
    assert post4.target_name == "明日方舟更新信息"


@pytest.mark.render()
@respx.mock
async def test_send_with_render(
    arknights,
    dummy_user_subinfo,
    arknights_list_0,
    arknights_list_1,
    monster_siren_list_0,
    monster_siren_list_1,
):
    from nonebot_bison.types import Target, SubUnit

    ak_list_router = respx.get("https://ak-webview.hypergryph.com/api/game/bulletinList?target=IOS")
    detail_router = respx.get("https://ak-webview.hypergryph.com/api/game/bulletin/8397")
    version_router = respx.get("https://ak-conf.hypergryph.com/config/prod/official/IOS/version")
    preannouncement_router = respx.get(
        "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json"
    )
    monster_siren_router = respx.get("https://monster-siren.hypergryph.com/api/news")
    terra_list = respx.get("https://terra-historicus.hypergryph.com/api/recentUpdate")

    ak_list_router.mock(return_value=Response(200, json=arknights_list_0))
    detail_router.mock(return_value=Response(200, text=get_file("arknights-detail-805")))
    version_router.mock(return_value=Response(200, json=get_json("arknights-version-0.json")))
    preannouncement_router.mock(return_value=Response(200, json=get_json("arknights-pre-0.json")))
    monster_siren_router.mock(return_value=Response(200, json=monster_siren_list_0))
    terra_list.mock(return_value=Response(200, json=get_json("terra-hist-0.json")))
    target = Target("")
    res1 = await arknights.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert ak_list_router.called
    assert len(res1) == 0
    assert not detail_router.called

    mock_data = arknights_list_1
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res2 = await arknights.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res2[0][1]) == 1
    assert detail_router.called
    post2 = res2[0][1][0]
    assert post2.theme == "arknights"
    assert post2.card_data.announce_title == "【公开招募】标签强制刷新通知"
    assert post2.card_data.content
