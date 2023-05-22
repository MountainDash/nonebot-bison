import pytest
import respx
from httpx import AsyncClient, Response
from nonebug.app import App

from .utils import get_file, get_json


@pytest.fixture
def arknights(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import ProcessContext

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


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(
    arknights,
    dummy_user_subinfo,
    arknights_list_0,
    arknights_list__1,
    monster_siren_list_0,
    monster_siren_list_1,
):
    ak_list_router = respx.get(
        "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/announcement.meta.json"
    )
    detail_router = respx.get(
        "https://ak.hycdn.cn/announce/IOS/announcement/807_1640060583.html"
    )
    version_router = respx.get(
        "https://ak-conf.hypergryph.com/config/prod/official/IOS/version"
    )
    preannouncement_router = respx.get(
        "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json"
    )
    monster_siren_router = respx.get("https://monster-siren.hypergryph.com/api/news")
    monster_siren_details_router = respx.get(
        "https://monster-siren.hypergryph.com/api/news/241303"
    )
    terra_list = respx.get("https://terra-historicus.hypergryph.com/api/recentUpdate")
    ak_list_router.mock(return_value=Response(200, json=arknights_list__1))
    detail_router.mock(
        return_value=Response(200, text=get_file("arknights-detail-807"))
    )
    version_router.mock(
        return_value=Response(200, json=get_json("arknights-version-0.json"))
    )
    preannouncement_router.mock(
        return_value=Response(200, json=get_json("arknights-pre-0.json"))
    )
    monster_siren_router.mock(return_value=Response(200, json=monster_siren_list_0))
    monster_siren_details_router.mock(
        return_value=Response(200, json=get_json("monster-siren-details-241303.json"))
    )
    terra_list.mock(return_value=Response(200, json=get_json("terra-hist-0.json")))
    target = ""
    res = await arknights.fetch_new_post(target, [dummy_user_subinfo])
    assert ak_list_router.called
    assert len(res) == 0
    assert not detail_router.called
    mock_data = arknights_list_0
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res3 = await arknights.fetch_new_post(target, [dummy_user_subinfo])
    assert len(res3[0][1]) == 1
    assert detail_router.called
    post = res3[0][1][0]
    assert post.target_type == "arknights"
    assert post.text == ""
    assert post.url == ""
    assert post.target_name == "明日方舟游戏内公告"
    assert len(post.pics) == 1
    # assert(post.pics == ['https://ak-fs.hypergryph.com/announce/images/20210623/e6f49aeb9547a2278678368a43b95b07.jpg'])
    print(res3[0][1])
    await post.generate_messages()
    terra_list.mock(return_value=Response(200, json=get_json("terra-hist-1.json")))
    res = await arknights.fetch_new_post(target, [dummy_user_subinfo])
    assert len(res) == 1
    post = res[0][1][0]
    assert post.target_type == "terra-historicus"
    assert post.text == "123罗德岛！？ - 「掠风」篇"
    assert post.url == "https://terra-historicus.hypergryph.com/comic/6253/episode/4938"
    assert post.pics == [
        "https://web.hycdn.cn/comic/pic/20220507/ab8a2ff408ec7d587775aed70b178ec0.png"
    ]
    assert post.card.dict() == {
        "type": "live",
        "header": {
            "face": "https://web.hycdn.cn/comic/site/manifest/icon-128x128.png",
            "name": "123罗德岛！？",
            "desc": "你可能不知道的罗德岛小剧场！",
            "platform": "泰拉记事社漫画",
        },
        "content": {
            "text": "「掠风」篇",
            "cover": "https://web.hycdn.cn/comic/pic/20220507/ab8a2ff408ec7d587775aed70b178ec0.png",
        },
        "extra_head": None,
    }
    monster_siren_router.mock(return_value=Response(200, json=monster_siren_list_1))
    res2 = await arknights.fetch_new_post(target, [dummy_user_subinfo])
    assert monster_siren_details_router.called
    assert len(res2) == 1
    post = res2[0][1][0]
    assert post.target_type == "monster-siren"
    assert post.card.dict() == {
        "type": "common",
        "header": {
            "face": "https://web.hycdn.cn/siren/site/favicon.ico",
            "name": "塞壬唱片",
            "desc": "2021-06-29  #D.D.D.PHOTO",
            "platform": "塞壬唱片新闻",
        },
        "content": {
            "text": '<p>有趣的新发现。</p><p>经纪人给的青草汁有着无比奇妙的味道O.O</p><p>难……难喝！</p><p></p><p>咳咳，不是。</p><p></p><div class="media-wrap image-wrap"><img id="cb0723afc433bcbabbcdb12a3ea4ff2c" title="6.29-01.jpg" alt="6.29-01.jpg" poster="" src="https://web.hycdn.cn/siren/pic/20210625/cb0723afc433bcbabbcdb12a3ea4ff2c.jpg"/></div><p></p><p>安静的植物口味，毛毛雨一样微涩的口感，</p><p>还有好像在躲猫猫似的香气！</p><p>岂不是和音乐一模一样。</p><p>也许会是一种全新的风格呢，</p><p>我准备好把它们记录下来了XD</p>'
        },
        "extra_head": "\n        <style>\n        .content img {\n            width: 100%;\n            height: auto;\n            display: block;\n            margin: 0 auto;\n        }\n        </style>\n        ",
    }


@pytest.mark.render
@respx.mock
async def test_send_with_render(
    arknights,
    dummy_user_subinfo,
    arknights_list_0,
    arknights_list_1,
    monster_siren_list_0,
    monster_siren_list_1,
):
    ak_list_router = respx.get(
        "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/announcement.meta.json"
    )
    detail_router = respx.get(
        "https://ak.hycdn.cn/announce/IOS/announcement/805_1640074952.html"
    )
    version_router = respx.get(
        "https://ak-conf.hypergryph.com/config/prod/official/IOS/version"
    )
    preannouncement_router = respx.get(
        "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json"
    )
    monster_siren_router = respx.get("https://monster-siren.hypergryph.com/api/news")
    terra_list = respx.get("https://terra-historicus.hypergryph.com/api/recentUpdate")
    ak_list_router.mock(return_value=Response(200, json=arknights_list_0))
    detail_router.mock(
        return_value=Response(200, text=get_file("arknights-detail-805"))
    )
    version_router.mock(
        return_value=Response(200, json=get_json("arknights-version-0.json"))
    )
    preannouncement_router.mock(
        return_value=Response(200, json=get_json("arknights-pre-0.json"))
    )
    monster_siren_router.mock(return_value=Response(200, json=monster_siren_list_0))
    terra_list.mock(return_value=Response(200, json=get_json("terra-hist-0.json")))
    target = ""
    res = await arknights.fetch_new_post(target, [dummy_user_subinfo])
    assert ak_list_router.called
    assert len(res) == 0
    assert not detail_router.called
    mock_data = arknights_list_1
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res3 = await arknights.fetch_new_post(target, [dummy_user_subinfo])
    assert len(res3[0][1]) == 1
    assert detail_router.called
    post = res3[0][1][0]
    assert post.target_type == "arknights"
    assert post.text == ""
    assert post.url == ""
    assert post.target_name == "明日方舟游戏内公告"
    assert len(post.pics) == 1
    # assert(post.pics == ['https://ak-fs.hypergryph.com/announce/images/20210623/e6f49aeb9547a2278678368a43b95b07.jpg'])
    print(res3[0][1])
    r = await post.generate_messages()
