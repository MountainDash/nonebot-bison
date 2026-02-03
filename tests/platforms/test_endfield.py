from copy import deepcopy

from httpx import Response
from nonebot.compat import type_validate_python
from nonebug.app import App
import pytest
import respx

from .utils import get_json


@pytest.fixture
def endfield(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    return platform_manager["endfield"](ProcessContext(DefaultClientManager()))


@pytest.fixture(scope="module")
def endfield_list_0():
    return get_json("endfield_list_0.json")


@pytest.fixture(scope="module")
def endfield_detail_9883():
    return get_json("endfield-detail-9883.json")


@pytest.fixture(scope="module")
def endfield_detail_7202():
    return get_json("endfield-detial-7202.json")


@pytest.mark.asyncio
@respx.mock
async def test_parse_picture(app: App, endfield, endfield_list_0, endfield_detail_9883):
    from nonebot_bison.platform.endfield import BulletinListItem

    detail_router = respx.get("https://game-hub.hypergryph.com/bulletin/detail/9883?lang=zh-cn&code=endfield_5SD9TN")
    detail_router.mock(return_value=Response(200, json=endfield_detail_9883))

    raw_item = next(item for item in endfield_list_0["data"]["list"] if item["cid"] == "9883")
    raw_post = type_validate_python(BulletinListItem, raw_item)

    post = await endfield.parse(raw_post)
    assert detail_router.called
    assert post.title == "预抽卡活动"
    assert post.content == ""
    assert post.images == ["https://web.hycdn.cn/upload/image/20260121/e1e0452b684b22b0379bb7f9881fb6cb.jpg"]
    assert post.url == "https://endfield.hypergryph.com/activity/final-prep-orders?source_from=game"
    assert post.nickname == "终末地游戏内公告"


@pytest.mark.asyncio
@respx.mock
async def test_parse_rich_text(app: App, endfield, endfield_list_0, endfield_detail_7202):
    from nonebot_bison.platform.endfield import BulletinListItem

    detail_router = respx.get("https://game-hub.hypergryph.com/bulletin/detail/7202?lang=zh-cn&code=endfield_5SD9TN")
    detail_router.mock(return_value=Response(200, json=endfield_detail_7202))

    raw_item = next(item for item in endfield_list_0["data"]["list"] if item["cid"] == "7202")
    raw_post = type_validate_python(BulletinListItem, raw_item)

    post = await endfield.parse(raw_post)
    assert detail_router.called
    assert post.title == "游戏历程体验问卷"
    assert post.content == endfield_detail_7202["data"]["data"]["html"]
    assert post.images is None
    assert post.url == ""
    assert post.nickname == "终末地游戏内公告"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_post(app: App, endfield, dummy_user_subinfo, endfield_list_0, endfield_detail_9883):
    from nonebot_bison.platform.arknights import ArknightsPost
    from nonebot_bison.types import SubUnit, Target

    list_router = respx.get(
        "https://game-hub.hypergryph.com/bulletin/v2/aggregate?lang=zh-cn&platform=Windows&channel=1&subChannel=1&type=1&code=endfield_5SD9TN&hideDetail=1"
    )
    detail_router = respx.get("https://game-hub.hypergryph.com/bulletin/detail/9883?lang=zh-cn&code=endfield_5SD9TN")
    detail_router.mock(return_value=Response(200, json=endfield_detail_9883))

    list_empty = deepcopy(endfield_list_0)
    list_empty["data"]["list"] = []

    list_single = deepcopy(endfield_list_0)
    list_single["data"]["list"] = [item for item in endfield_list_0["data"]["list"] if item["cid"] == "9883"]

    list_router.mock(return_value=Response(200, json=list_empty))
    target = Target("")
    res1 = await endfield.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert list_router.called
    assert not detail_router.called
    assert res1 == []

    list_router.mock(return_value=Response(200, json=list_single))
    res2 = await endfield.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert detail_router.called
    assert len(res2) == 1
    post2: ArknightsPost = res2[0][1][0]
    assert post2.title == "预抽卡活动"
    assert post2.images == ["https://web.hycdn.cn/upload/image/20260121/e1e0452b684b22b0379bb7f9881fb6cb.jpg"]
    assert post2.url == "https://endfield.hypergryph.com/activity/final-prep-orders?source_from=game"
    assert post2.nickname == "终末地游戏内公告"
