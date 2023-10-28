from asyncio import sleep
from typing import TYPE_CHECKING

import respx
import pytest
from nonebug.app import App
from httpx import Response, AsyncClient

from .utils import get_json

if TYPE_CHECKING:
    from nonebot_bison.platform.ceobecanteen import CeobeCanteen


@pytest.fixture()
def dummy_only_open_user_subinfo(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.types import UserSubInfo

    user = TargetQQGroup(group_id=123)
    return UserSubInfo(user=user, categories=[1], tags=[])


@pytest.fixture()
def ceobecanteen(app: App):
    from nonebot_bison.utils import ProcessContext
    from nonebot_bison.platform import platform_manager

    return platform_manager["ceobecanteen"](ProcessContext(), AsyncClient())


@pytest.fixture(scope="module")
def dummy_target() -> str:
    return "7d23708b-e424-418b-b4c4-43c370c3b6d0"


@pytest.fixture(scope="module")
def ceobecanteen_targets() -> dict:
    return get_json("ceobecanteen_targets.json")


@pytest.fixture(scope="module")
def ceobecanteen_comb_id_0() -> dict:
    return get_json("ceobecanteen_comb_id_0.json")


@pytest.fixture(scope="module")
def ceobecanteen_comb_id_1() -> dict:
    return get_json("ceobecanteen_comb_id_1.json")


@pytest.fixture(scope="module")
def ceobecanteen_cookie_id_0() -> dict:
    return get_json("ceobecanteen_cookie_id_0.json")


@pytest.fixture(scope="module")
def ceobecanteen_cookie_id_1() -> dict:
    return get_json("ceobecanteen_cookie_id_1.json")


@pytest.fixture(scope="module")
def ceobecanteen_cookies_0() -> dict:
    return get_json("ceobecanteen_cookies_0.json")


@pytest.fixture(scope="module")
def ceobecanteen_cookies_1() -> dict:
    return get_json("ceobecanteen_cookies_1.json")


@pytest.mark.asyncio()
@respx.mock
async def test_simple_cache(app: App):
    from datetime import timedelta

    from nonebot_bison.platform.ceobecanteen.cache import SimpleCache

    cache = SimpleCache()
    cache["key"] = (1, timedelta(seconds=1))

    assert cache["key"] == 1
    assert cache.get("key", value_convert_func=str) == "1"
    await sleep(1)
    assert not cache["key"]

    cache.set("key2", 2, timedelta(seconds=1))
    assert cache["key2"] == 2


@pytest.mark.asyncio()
@respx.mock
async def test_batch_fetch_new_with_single(
    app: App,
    dummy_target,
    dummy_only_open_user_subinfo,
    ceobecanteen: "CeobeCanteen",
    ceobecanteen_targets,
    ceobecanteen_comb_id_0,
    ceobecanteen_cookie_id_0,
    ceobecanteen_cookie_id_1,
    ceobecanteen_cookies_0,
    ceobecanteen_cookies_1,
):
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit

    targets_router = respx.get("https://server.ceobecanteen.top/api/v1/canteen/config/datasource/list")
    comb_id_router = respx.post("https://server.ceobecanteen.top/api/v1/canteen/user/getDatasourceComb")
    cookie_id_router = respx.get("http://cdn.ceobecanteen.top/datasource-comb/2")
    cookies_router = respx.get("https://server-cdn.ceobecanteen.top/api/v1/cdn/cookie/mainList/cookieList")

    targets_router.mock(return_value=Response(200, json=ceobecanteen_targets))
    comb_id_router.mock(return_value=Response(200, json=ceobecanteen_comb_id_0))
    cookie_id_router.mock(return_value=Response(200, json=ceobecanteen_cookie_id_0))
    cookies_router.mock(return_value=Response(200, json=ceobecanteen_cookies_0))

    assert await ceobecanteen.get_target_name(None, dummy_target) == "明日方舟-B站"
    assert await ceobecanteen.parse_target("明日方舟-B站") == dummy_target

    res1 = await ceobecanteen.batch_fetch_new_post([SubUnit(dummy_target, [dummy_only_open_user_subinfo])])
    assert comb_id_router.called
    assert cookie_id_router.called
    assert cookies_router.called
    assert res1 == []

    res2 = await ceobecanteen.batch_fetch_new_post([SubUnit(dummy_target, [dummy_only_open_user_subinfo])])
    assert comb_id_router.call_count == 1
    assert cookie_id_router.call_count == 2
    assert cookies_router.call_count == 1
    assert res2 == []

    cookie_id_router.mock(return_value=Response(200, json=ceobecanteen_cookie_id_1))
    cookies_router.mock(return_value=Response(200, json=ceobecanteen_cookies_1))
    res3 = await ceobecanteen.batch_fetch_new_post([SubUnit(dummy_target, [dummy_only_open_user_subinfo])])
    assert comb_id_router.call_count == 1
    assert cookie_id_router.call_count == 3
    assert cookies_router.call_count == 2

    post3: Post = res3[0][1][0]
    assert not post3.title
    assert (
        post3.content
        == "【新增服饰】\n//正午余光 - 苦艾\nEPOQUE子品牌 [昔时/Passe]系列精选款/正午余光。苦艾曾经的校服。"
        "在乌萨斯，学生穿校服出操，就像是跟在一把犁后面一行整齐的秧苗。\n\n_____________\n只可惜，"
        "阳光能照在这把犁上的时间总是太短了。但这样的事，那个春天之前的她还不明白。"
    )
    assert post3.images
    assert len(post3.images) == 6
    assert post3.timestamp
    assert post3.url
    assert post3.avatar
    assert post3.nickname == "明日方舟-B站"
    assert post3.description
