from time import time

from httpx import Response
from nonebot.compat import model_dump, type_validate_python
from nonebug.app import App
import pytest
import respx

from .utils import get_file, get_json


@pytest.fixture
def arknights(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    return platform_manager["arknights"](ProcessContext(DefaultClientManager()))


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


@respx.mock
async def test_url_parse(app: App):
    from nonebot_bison.platform.arknights import ArkBulletinResponse, Arknights, BulletinData, BulletinListItem
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    cid_router = respx.get("https://ak-webview.hypergryph.com/api/game/bulletin/1")

    def make_bulletin_obj(jump_link: str):
        return type_validate_python(
            BulletinData,
            {
                "cid": "1",
                "displayType": 1,
                "title": "title",
                "category": 1,
                "header": "header",
                "content": "content",
                "jumpLink": jump_link,
                "bannerImageUrl": "https://www.baidu.com",
                "displayTime": "2021-08-01",
                "updatedAt": 1627795200,
            },
        )

    def make_bulletin_list_item_obj():
        return BulletinListItem(
            cid="1",
            title="title",
            category=1,
            displayTime="2021-08-01",
            updatedAt=1627795200,
            sticky=False,
        )

    def make_response(b: BulletinData):
        return Response(200, json=model_dump(ArkBulletinResponse(code=0, msg="", data=b), by_alias=True))

    b1 = make_bulletin_obj("")
    assert b1.jump_link == ""

    b2 = make_bulletin_obj("uniwebview://move?target=shop&param1=SKINSHOP")
    assert b2.jump_link == "uniwebview://move?target=shop&param1=SKINSHOP"

    b3 = make_bulletin_obj("https://www.baidu.com")
    assert b3.jump_link == "https://www.baidu.com"

    b4 = make_bulletin_obj("http://www.baidu.com")
    assert b4.jump_link == "http://www.baidu.com"

    ark = Arknights(ProcessContext(DefaultClientManager()))

    cid_router.mock(return_value=make_response(b1))
    p1 = await ark.parse(make_bulletin_list_item_obj())
    assert p1.url is None

    cid_router.mock(return_value=make_response(b2))
    p2 = await ark.parse(make_bulletin_list_item_obj())
    assert p2.url is None

    cid_router.mock(return_value=make_response(b3))
    p3 = await ark.parse(make_bulletin_list_item_obj())
    assert p3.url == "https://www.baidu.com/"

    cid_router.mock(return_value=make_response(b4))
    p4 = await ark.parse(make_bulletin_list_item_obj())
    assert p4.url == "http://www.baidu.com/"


@pytest.mark.asyncio
async def test_get_date_in_bulletin(app: App):
    from nonebot_bison.platform.arknights import Arknights, BulletinListItem
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    arknights = Arknights(ProcessContext(DefaultClientManager()))
    assert (
        arknights.get_date(
            BulletinListItem(
                cid="1",
                title="",
                category=1,
                displayTime="",
                updatedAt=1627036800,
                sticky=False,
            )
        )
        is None
    )


@pytest.mark.asyncio
@respx.mock
async def test_parse_with_breakline(app: App):
    from nonebot_bison.platform.arknights import Arknights, BulletinListItem
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    detail = get_json("arknights-detail-805")
    detail["data"]["header"] = ""

    arknights = Arknights(ProcessContext(DefaultClientManager()))

    router = respx.get("https://ak-webview.hypergryph.com/api/game/bulletin/1")
    router.mock(return_value=Response(200, json=detail))

    post = await arknights.parse(
        BulletinListItem(
            cid="1",
            title="【公开招募】\\n标签刷新通知",
            category=1,
            displayTime="",
            updatedAt=1627036800,
            sticky=False,
        )
    )
    assert post.title == "【公开招募】 - 标签刷新通知"


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
    from nonebot_bison.platform.arknights import ArknightsPost
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit, Target

    ak_list_router = respx.get("https://ak-webview.hypergryph.com/api/game/bulletinList?target=IOS")
    detail_router = respx.get("https://ak-webview.hypergryph.com/api/game/bulletin/5716")
    version_router = respx.get("https://ak-conf.hypergryph.com/config/prod/official/IOS/version")
    preannouncement_router = respx.get(
        "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json"
    )
    monster_siren_router = respx.get("https://monster-siren.hypergryph.com/api/news")
    terra_list = respx.get("https://terra-historicus.hypergryph.com/api/recentUpdate")
    ak_list_router.mock(return_value=Response(200, json=arknights_list__1))
    mock_detail = get_json("arknights-detail-807")
    mock_detail["data"]["bannerImageUrl"] = "https://example.com/1.jpg"
    detail_router.mock(return_value=Response(200, json=mock_detail))
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
    mock_data["data"]["list"][0]["updatedAt"] = int(time())
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res2 = await arknights.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res2[0][1]) == 1
    assert detail_router.called
    post2: ArknightsPost = res2[0][1][0]
    assert post2.platform.platform_name == "arknights"
    assert post2.content
    assert post2.title == "2023「夏日嘉年华」限时活动即将开启"
    assert not post2.url
    assert post2.nickname == "明日方舟游戏内公告"
    assert post2.images
    assert post2.images == ["https://example.com/1.jpg"]
    assert post2.timestamp
    assert "arknights" == post2.get_priority_themes()[0]
    # assert(post.pics == ['https://ak-fs.hypergryph.com/announce/images/20210623/e6f49aeb9547a2278678368a43b95b07.jpg'])
    post2_plain_content = await post2.get_plain_content()
    assert post2_plain_content.strip() == get_file("arknights-plaintext-807.txt").strip()
    assert await post2.generate()
    terra_list.mock(return_value=Response(200, json=get_json("terra-hist-1.json")))
    res3 = await arknights.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res3) == 1
    post3: Post = res3[0][1][0]
    assert post3.platform.platform_name == "arknights"
    assert post3.nickname == "泰拉记事社漫画"
    assert post3.title == "123罗德岛！？ - 「掠风」篇"
    assert post3.content == "你可能不知道的罗德岛小剧场！"
    assert post3.url == "https://terra-historicus.hypergryph.com/comic/6253/episode/4938"
    assert post3.images == ["https://web.hycdn.cn/comic/pic/20220507/ab8a2ff408ec7d587775aed70b178ec0.png"]
    assert "brief" == post3.get_priority_themes()[0]


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
    from nonebot_bison.platform.arknights import ArknightsPost
    from nonebot_bison.types import SubUnit, Target

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
    mock_data["data"]["list"][0]["updatedAt"] = int(time())
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res2 = await arknights.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res2[0][1]) == 1
    assert detail_router.called
    post2: ArknightsPost = res2[0][1][0]
    assert post2.platform.platform_name == "arknights"
    assert post2.content
    post2_plain_content = await post2.get_plain_content()
    assert post2_plain_content.strip() == get_file("arknights-plaintext-805.txt").strip()
    assert await post2.generate()
    assert post2.title == "【公开招募】标签强制刷新通知"
    assert post2.nickname == "明日方舟游戏内公告"
    assert not post2.images
    # assert(post.pics == ['https://ak-fs.hypergryph.com/announce/images/20210623/e6f49aeb9547a2278678368a43b95b07.jpg'])
    r = await post2.generate_messages()
    assert r


@pytest.mark.render
@respx.mock
async def test_parse_title(
    app: App,
):
    from nonebot_bison.platform.arknights import Arknights, BulletinListItem
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    detail_router = respx.get("https://ak-webview.hypergryph.com/api/game/bulletin/8397")

    ark = Arknights(ProcessContext(DefaultClientManager()))

    mock_detail = get_json("arknights-detail-805")
    mock_detail["data"]["header"] = ""

    detail_router.mock(return_value=Response(200, json=mock_detail))

    mock_raw_post = BulletinListItem(
        cid="8397",
        title="【公开招募】\n标签刷新通知",
        category=1,
        displayTime="07-30 10:00:00",
        updatedAt=1627582800,
        sticky=False,
    )
    post = await ark.parse(mock_raw_post)
    assert post.title == "【公开招募】 - 标签刷新通知"
