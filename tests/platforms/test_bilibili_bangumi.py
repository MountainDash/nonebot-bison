import typing

import respx
import pytest
from nonebug.app import App
from httpx import Response, AsyncClient

from .utils import get_json

if typing.TYPE_CHECKING:
    from nonebot_bison.platform.bilibili import BilibiliBangumi


@pytest.fixture()
def bili_bangumi(app: App):
    from nonebot_bison.utils import ProcessContext
    from nonebot_bison.platform import platform_manager

    return platform_manager["bilibili-bangumi"](ProcessContext(), AsyncClient())


async def test_parse_target(bili_bangumi: "BilibiliBangumi"):
    from nonebot_bison.platform.platform import Platform

    res1 = await bili_bangumi.parse_target("28339726")
    assert res1 == "28339726"
    res2 = await bili_bangumi.parse_target("md28339726")
    assert res2 == "28339726"
    res3 = await bili_bangumi.parse_target("https://www.bilibili.com/bangumi/media/md28339726")
    assert res3 == "28339726"
    with pytest.raises(Platform.ParseTargetException):
        await bili_bangumi.parse_target("https://www.bilibili.com/bangumi/play/ep683045")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bilibili_bangumi_status(bili_bangumi: "BilibiliBangumi", dummy_user_subinfo):
    from nonebot_bison.types import Target, SubUnit

    bili_bangumi_router = respx.get("https://api.bilibili.com/pgc/review/user?media_id=28235413")
    bili_bangumi_detail_router = respx.get("https://api.bilibili.com/pgc/view/web/season?season_id=39719")
    bili_bangumi_router.mock(return_value=Response(200, json=get_json("bilibili-gangumi-hanhua0.json")))
    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))
    target = Target("28235413")
    res = await bili_bangumi.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res) == 0

    res = await bili_bangumi.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res) == 0

    bili_bangumi_router.mock(return_value=Response(200, json=get_json("bilibili-gangumi-hanhua1.json")))
    bili_bangumi_detail_router.mock(return_value=Response(200, json=get_json("bilibili-gangumi-hanhua1-detail.json")))
    res2 = await bili_bangumi.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))

    post = res2[0][1][0]
    assert post.paltform_name == "Bilibili剧集"
    assert post.content == "《汉化日记 第三季》第2话 什么是战区导弹防御系统工作日"
    assert post.url == "https://www.bilibili.com/bangumi/play/ep519207"
    assert post.nickname == "汉化日记 第三季"
    assert post.images == ["http://i0.hdslb.com/bfs/archive/ea0a302c954f9dbc3d593e676486396c551529c9.jpg"]
    assert post.compress is True
