from copy import deepcopy
from typing import TYPE_CHECKING

from httpx import Response
from nonebug.app import App
import pytest
import respx

from .utils import get_json

if TYPE_CHECKING:
    from nonebot_bison.platform.bilibili import Bilibililive


@pytest.fixture
def bili_live(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    return platform_manager["bilibili-live"](ProcessContext(DefaultClientManager()))


@pytest.fixture
def dummy_only_open_user_subinfo(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.types import UserSubInfo

    user = TargetQQGroup(group_id=123)
    return UserSubInfo(user=user, categories=[1], tags=[])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bililive_no_room(bili_live, dummy_only_open_user_subinfo):
    from nonebot_bison.types import SubUnit, Target

    mock_bili_live_status = get_json("bili_live_status.json")
    mock_bili_live_status["data"] = {}
    bili_live_router = respx.get("https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids[]=13164144")
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))

    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))

    target = Target("13164144")
    res = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_open_user_subinfo]))])
    assert bili_live_router.call_count == 1
    assert len(res) == 0


@pytest.mark.asyncio
@respx.mock
async def test_fetch_first_live(bili_live, dummy_only_open_user_subinfo):
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit, Target

    mock_bili_live_status = get_json("bili_live_status.json")
    empty_bili_live_status = deepcopy(mock_bili_live_status)
    empty_bili_live_status["data"] = {}
    bili_live_router = respx.get("https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids[]=13164144")
    bili_live_router.mock(return_value=Response(200, json=empty_bili_live_status))

    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))

    target = Target("13164144")

    res1 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_open_user_subinfo]))])
    assert bili_live_router.call_count == 1
    assert len(res1) == 0

    mock_bili_live_status["data"][target]["live_status"] = 1
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res2 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_open_user_subinfo]))])
    assert bili_live_router.call_count == 2
    assert len(res2) == 1
    post2: Post = res2[0][1][0]
    assert post2.platform.name == "Bilibili直播"
    assert post2.title == "[开播] 【Zc】从0挑战到15肉鸽！目前10难度"
    assert post2.content == ""
    assert post2.url == "https://live.bilibili.com/3044248"
    assert post2.nickname == "魔法Zc目录 其他单机"
    assert post2.images == ["https://i0.hdslb.com/bfs/live/new_room_cover/fd357f0f3cbbb48e9acfbcda616b946c2454c56c.jpg"]
    assert post2.compress is True
    assert "brief" == post2.get_priority_themes()[0]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bililive_only_live_open(bili_live: "Bilibililive", dummy_only_open_user_subinfo):
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit, Target

    mock_bili_live_status = get_json("bili_live_status.json")

    bili_live_router = respx.get("https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids[]=13164144")
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))

    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))

    target = Target("13164144")

    bili_live.set_stored_data(target, None)
    res1 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_open_user_subinfo]))])
    assert bili_live_router.call_count == 1
    assert len(res1) == 0
    # 直播状态更新-上播
    mock_bili_live_status["data"][target]["live_status"] = 1
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res2 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_open_user_subinfo]))])
    post2: Post = res2[0][1][0]
    assert post2.platform.name == "Bilibili直播"
    assert post2.title == "[开播] 【Zc】从0挑战到15肉鸽！目前10难度"
    assert post2.url == "https://live.bilibili.com/3044248"
    assert post2.nickname == "魔法Zc目录 其他单机"
    assert post2.images == ["https://i0.hdslb.com/bfs/live/new_room_cover/fd357f0f3cbbb48e9acfbcda616b946c2454c56c.jpg"]
    assert post2.compress is True
    # 标题变更
    mock_bili_live_status["data"][target]["title"] = "【Zc】从0挑战到15肉鸽！目前11难度"
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res3 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_open_user_subinfo]))])
    assert bili_live_router.call_count == 3
    assert len(res3[0][1]) == 0
    # 直播状态更新-下播
    mock_bili_live_status["data"][target]["live_status"] = 0
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res4 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_open_user_subinfo]))])
    assert bili_live_router.call_count == 4
    assert len(res4[0][1]) == 0


@pytest.fixture
def dummy_only_title_user_subinfo(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.types import UserSubInfo

    user = TargetQQGroup(group_id=123)
    return UserSubInfo(user=user, categories=[2], tags=[])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bililive_only_title_change(bili_live, dummy_only_title_user_subinfo):
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit, Target

    mock_bili_live_status = get_json("bili_live_status.json")
    target = Target("13164144")

    bili_live_router = respx.get("https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids[]=13164144")
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))

    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))

    res = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_title_user_subinfo]))])
    assert bili_live_router.call_count == 1
    assert len(res) == 0
    # 未开播前标题变更
    mock_bili_live_status["data"][target]["title"] = "【Zc】从0挑战到15肉鸽！目前11难度"
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res0 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_title_user_subinfo]))])
    assert bili_live_router.call_count == 2
    assert len(res0) == 0
    # 直播状态更新-上播
    mock_bili_live_status["data"][target]["live_status"] = 1
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res2 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_title_user_subinfo]))])
    assert bili_live_router.call_count == 3
    assert len(res2[0][1]) == 0
    # 标题变更
    mock_bili_live_status["data"][target]["title"] = "【Zc】从0挑战到15肉鸽！目前12难度"
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res3 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_title_user_subinfo]))])
    post3: Post = res3[0][1][0]
    assert post3.platform.name == "Bilibili直播"
    assert post3.title == "[标题更新] 【Zc】从0挑战到15肉鸽！目前12难度"
    assert post3.url == "https://live.bilibili.com/3044248"
    assert post3.nickname == "魔法Zc目录 其他单机"
    assert post3.images == ["https://i0.hdslb.com/bfs/live-key-frame/keyframe10170435000003044248mwowx0.jpg"]
    assert post3.compress is True
    # 直播状态更新-下播
    mock_bili_live_status["data"][target]["live_status"] = 0
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res4 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_title_user_subinfo]))])
    assert bili_live_router.call_count == 5
    assert len(res4[0][1]) == 0


@pytest.fixture
def dummy_only_close_user_subinfo(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.types import UserSubInfo

    user = TargetQQGroup(group_id=123)
    return UserSubInfo(user=user, categories=[3], tags=[])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bililive_only_close(bili_live, dummy_only_close_user_subinfo):
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit, Target

    mock_bili_live_status = get_json("bili_live_status.json")
    target = Target("13164144")

    bili_live_router = respx.get("https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids[]=13164144")
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))

    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))

    res = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_close_user_subinfo]))])
    assert bili_live_router.call_count == 1
    assert len(res) == 0
    # 未开播前标题变更
    mock_bili_live_status["data"][target]["title"] = "【Zc】从0挑战到15肉鸽！目前11难度"
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res0 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_close_user_subinfo]))])
    assert bili_live_router.call_count == 2
    assert len(res0) == 0
    # 直播状态更新-上播
    mock_bili_live_status["data"][target]["live_status"] = 1
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res2 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_close_user_subinfo]))])
    assert bili_live_router.call_count == 3
    assert len(res2[0][1]) == 0
    # 标题变更
    mock_bili_live_status["data"][target]["title"] = "【Zc】从0挑战到15肉鸽！目前12难度"
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res3 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_close_user_subinfo]))])
    assert bili_live_router.call_count == 4
    assert len(res3[0][1]) == 0
    # 直播状态更新-下播
    mock_bili_live_status["data"][target]["live_status"] = 0
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res4 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_only_close_user_subinfo]))])
    assert bili_live_router.call_count == 5
    post4: Post = res4[0][1][0]
    assert post4.platform.name == "Bilibili直播"
    assert post4.title == "[下播] 【Zc】从0挑战到15肉鸽！目前12难度"
    assert post4.url == "https://live.bilibili.com/3044248"
    assert post4.nickname == "魔法Zc目录 其他单机"
    assert post4.images == ["https://i0.hdslb.com/bfs/live-key-frame/keyframe10170435000003044248mwowx0.jpg"]
    assert post4.compress is True


@pytest.mark.asyncio
@respx.mock
async def test_bililive_close_and_no_keyframe(bili_live: "Bilibililive", dummy_only_close_user_subinfo):
    info = bili_live.Info(
        title="【Zc】从0挑战到15肉鸽！目前12难度",
        room_id=721,
        uid=13164144,
        live_time=114514,
        live_status=bili_live.LiveStatus.OFF,
        area_v2_name="其他单机",
        uname="魔法Zc目录",
        face="fake",
        cover_from_user="fake",
        keyframe="",
        category=3,  # 下播
    )
    post = await bili_live.parse(info)
    assert post.images == ["fake"]

    info.keyframe = "key_fake"
    post2 = await bili_live.parse(info)
    assert post2.images == ["key_fake"]


@pytest.fixture
def dummy_bililive_user_subinfo(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.types import UserSubInfo

    user = TargetQQGroup(group_id=123)
    return UserSubInfo(user=user, categories=[1, 2, 3], tags=[])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bililive_combo(bili_live, dummy_bililive_user_subinfo):
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit, Target

    mock_bili_live_status = get_json("bili_live_status.json")
    target = Target("13164144")

    bili_live_router = respx.get("https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids[]=13164144")
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))

    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))

    res = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_bililive_user_subinfo]))])
    assert bili_live_router.call_count == 1
    assert len(res) == 0
    # 未开播前标题变更
    mock_bili_live_status["data"][target]["title"] = "【Zc】从0挑战到15肉鸽！目前11难度"
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res0 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_bililive_user_subinfo]))])
    assert bili_live_router.call_count == 2
    assert len(res0) == 0
    # 直播状态更新-上播
    mock_bili_live_status["data"][target]["live_status"] = 1
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res2 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_bililive_user_subinfo]))])
    post2: Post = res2[0][1][0]
    assert post2.platform.name == "Bilibili直播"
    assert post2.title == "[开播] 【Zc】从0挑战到15肉鸽！目前11难度"
    assert post2.url == "https://live.bilibili.com/3044248"
    assert post2.nickname == "魔法Zc目录 其他单机"
    assert post2.images == ["https://i0.hdslb.com/bfs/live/new_room_cover/fd357f0f3cbbb48e9acfbcda616b946c2454c56c.jpg"]
    assert post2.compress is True
    # 标题变更
    mock_bili_live_status["data"][target]["title"] = "【Zc】从0挑战到15肉鸽！目前12难度"
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res3 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_bililive_user_subinfo]))])
    post3: Post = res3[0][1][0]
    assert post3.platform.name == "Bilibili直播"
    assert post3.title == "[标题更新] 【Zc】从0挑战到15肉鸽！目前12难度"
    assert post3.url == "https://live.bilibili.com/3044248"
    assert post3.nickname == "魔法Zc目录 其他单机"
    assert post3.images == ["https://i0.hdslb.com/bfs/live-key-frame/keyframe10170435000003044248mwowx0.jpg"]
    assert post3.compress is True
    # 直播状态更新-下播
    mock_bili_live_status["data"][target]["live_status"] = 0
    bili_live_router.mock(return_value=Response(200, json=mock_bili_live_status))
    res4 = await bili_live.batch_fetch_new_post([(SubUnit(target, [dummy_bililive_user_subinfo]))])
    post4: Post = res4[0][1][0]
    assert post4.platform.name == "Bilibili直播"
    assert post4.title == "[下播] 【Zc】从0挑战到15肉鸽！目前12难度"
    assert post4.url == "https://live.bilibili.com/3044248"
    assert post4.nickname == "魔法Zc目录 其他单机"
    assert post4.images == ["https://i0.hdslb.com/bfs/live-key-frame/keyframe10170435000003044248mwowx0.jpg"]
    assert post4.compress is True
