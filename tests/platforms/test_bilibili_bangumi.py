import typing

import pytest
import respx
from httpx import AsyncClient, Response
from nonebug.app import App

from .utils import get_json

if typing.TYPE_CHECKING:
    from nonebot_bison.platform.bilibili import BilibiliBangumi


@pytest.fixture
def bili_bangumi(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import ProcessContext

    return platform_manager["bilibili-bangumi"](ProcessContext(), AsyncClient())


@pytest.mark.asyncio
@respx.mock
async def test_fetch_bilibili_bangumi_status(
    bili_bangumi: "BilibiliBangumi", dummy_user_subinfo
):
    from nonebot_bison.types import Target

    bili_bangumi_router = respx.get(
        "https://api.bilibili.com/pgc/review/user?media_id=28235413"
    )
    bili_bangumi_detail_router = respx.get(
        "https://api.bilibili.com/pgc/view/web/season?season_id=39719"
    )
    bili_bangumi_router.mock(
        return_value=Response(200, json=get_json("bilibili-gangumi-hanhua0.json"))
    )
    bilibili_main_page_router = respx.get("https://www.bilibili.com/")
    bilibili_main_page_router.mock(return_value=Response(200))
    target = Target("28235413")
    res = await bili_bangumi.fetch_new_post(target, [dummy_user_subinfo])
    assert len(res) == 0

    res = await bili_bangumi.fetch_new_post(target, [dummy_user_subinfo])
    assert len(res) == 0

    bili_bangumi_router.mock(
        return_value=Response(200, json=get_json("bilibili-gangumi-hanhua1.json"))
    )
    bili_bangumi_detail_router.mock(
        return_value=Response(
            200, json=get_json("bilibili-gangumi-hanhua1-detail.json")
        )
    )
    res2 = await bili_bangumi.fetch_new_post(target, [dummy_user_subinfo])

    post = res2[0][1][0]
    assert post.target_type == "Bilibili剧集"
    assert post.text == "《汉化日记 第三季》第2话 什么是战区导弹防御系统工作日"
    assert post.url == "https://www.bilibili.com/bangumi/play/ep519207"
    assert post.target_name == "汉化日记 第三季"
    assert post.pics == [
        "http://i0.hdslb.com/bfs/archive/ea0a302c954f9dbc3d593e676486396c551529c9.jpg"
    ]
    assert post.compress == True
