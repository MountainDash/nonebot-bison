from typing import TYPE_CHECKING

from httpx import Response
from nonebot.compat import type_validate_python
from nonebug.app import App
import pytest
import respx

from .utils import get_json

if TYPE_CHECKING:
    from nonebot_bison.platform.ceobecanteen import CeobeCanteen


@pytest.fixture
def dummy_only_open_user_subinfo(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.types import UserSubInfo

    user = TargetQQGroup(group_id=123)
    return UserSubInfo(user=user, categories=[1], tags=[])


@pytest.fixture
def ceobecanteen(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.ceobecanteen.platform import CeobeCanteenClientManager
    from nonebot_bison.utils import ProcessContext

    return platform_manager["ceobecanteen"](ProcessContext(CeobeCanteenClientManager()))


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


@pytest.mark.asyncio
async def test_parse_retweet(app: App):
    from nonebot_bison.platform.ceobecanteen.models import CookiesResponse

    cookie_with_retweet = type_validate_python(CookiesResponse, get_json("ceobecanteen_cookies_with_retweet.json"))
    assert cookie_with_retweet.data.cookies[0].item.retweeted


@pytest.mark.render
async def test_ceobe_snapshot(app: App, ceobecanteen: "CeobeCanteen"):
    from nonebot_bison.platform.ceobecanteen.models import CeobeCookie

    sp_coolies = get_json("ceobe_special_cookies.json")

    # arknights-game:bulletin-list but not need to snapshot
    cookie_bulletin_type2 = type_validate_python(CeobeCookie, sp_coolies[0])
    assert cookie_bulletin_type2.source.type == "arknights-game:bulletin-list"
    post = await ceobecanteen.parse(cookie_bulletin_type2)
    assert post.images
    assert len(post.images) == 1
    assert post.content == "【联合行动】\n定向寻访开启"

    cookie_bulletin_type1 = type_validate_python(CeobeCookie, sp_coolies[1])
    post2 = await ceobecanteen.parse(cookie_bulletin_type1)
    assert post2.images
    assert len(post2.images) == 1
    assert not post2.content

    cookie_offical = type_validate_python(CeobeCookie, sp_coolies[2])
    post3 = await ceobecanteen.parse(cookie_offical)
    assert post3.images
    assert len(post3.images) == 1
    assert not post3.content

    cookie_common = type_validate_python(CeobeCookie, sp_coolies[3])
    post4 = await ceobecanteen.parse(cookie_common)
    assert post4.images
    assert len(post4.images) == 7
    assert post4.content


@pytest.mark.skip("极限测试, 不在CI中运行")
@pytest.mark.asyncio
async def test_parse_crazy(app: App, ceobecanteen):
    from nonebot_plugin_saa import Image

    from nonebot_bison.platform.ceobecanteen import CeobeCanteen
    from nonebot_bison.platform.ceobecanteen.models import CeobeCookie

    def show(p: bytes):
        import io

        from PIL import Image

        Image.open(io.BytesIO(p)).show()

    def ext(m: Image):
        d = m.data["image"]
        assert isinstance(d, bytes)
        return d

    assert isinstance(ceobecanteen, CeobeCanteen)

    cookie_offical = type_validate_python(CeobeCookie, get_json("ceobe_looooong_bulletin.json"))
    post4 = await ceobecanteen.parse(cookie_offical)
    show(ext((await post4.generate_messages())[0][0]))  # type: ignore


@pytest.mark.asyncio
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

    mock_respone_headers = {
        "Content-Encoding": "br",
        "Content-Type": "application/json; charset=utf-8",
        "Date": "Thu, 08 Jul 2021 14:00:00 GMT",
        # "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "Vary": "origin; access-control-request-method; access-control-request-headers",
    }

    targets_router = respx.get("https://server.ceobecanteen.top/api/v1/canteen/config/datasource/list")
    comb_id_router = respx.post("https://server.ceobecanteen.top/api/v1/canteen/user/getDatasourceComb")
    cookie_id_router = respx.get("https://cdn.ceobecanteen.top/datasource-comb/2")
    cookies_router = respx.get("https://server-cdn.ceobecanteen.top/api/v1/cdn/cookie/mainList/cookieList")

    targets_router.mock(return_value=Response(200, json=ceobecanteen_targets, headers=mock_respone_headers))
    comb_id_router.mock(return_value=Response(200, json=ceobecanteen_comb_id_0))
    cookie_id_router.mock(return_value=Response(200, json=ceobecanteen_cookie_id_0, headers=mock_respone_headers))
    cookies_router.mock(return_value=Response(200, json=ceobecanteen_cookies_0, headers=mock_respone_headers))

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
    assert len(post3.images) == 2
    assert post3.timestamp
    assert post3.url
    assert post3.avatar
    assert post3.nickname == "明日方舟-B站"
    assert post3.description
    assert post3.platform.platform_name == "ceobecanteen"

    image1_router = respx.get("https://i0.hdslb.com/bfs/new_dyn/62e053ba7efc18f15bfd195e2d2de984161775300.jpg")
    image2_router = respx.get("https://i0.hdslb.com/bfs/new_dyn/590a69665209ac220ea8a57f749d5267161775300.gif")
    image1_router.mock(return_value=Response(200, content=b"image1"))
    image2_router.mock(return_value=Response(200, content=b"image2"))
    await post3.generate_messages()


@pytest.mark.asyncio
@respx.mock
async def test_parse_target_fuzzy(app: App, ceobecanteen: "CeobeCanteen", dummy_target, ceobecanteen_targets):
    from nonebot_bison.platform.ceobecanteen import CeobeCanteen

    mock_respone_headers = {
        "Content-Encoding": "br",
        "Content-Type": "application/json; charset=utf-8",
        "Date": "Thu, 08 Jul 2021 14:00:00 GMT",
        # "Date": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "Vary": "origin; access-control-request-method; access-control-request-headers",
    }

    targets_router = respx.get("https://server.ceobecanteen.top/api/v1/canteen/config/datasource/list")
    targets_router.mock(return_value=Response(200, json=ceobecanteen_targets, headers=mock_respone_headers))

    # check load data ok
    assert await ceobecanteen.get_target_name(None, dummy_target) == "明日方舟-B站"
    assert await ceobecanteen.parse_target("明日方舟-B站") == dummy_target

    # check fuzzy search
    # try:
    #     assert await ceobecanteen.parse_target("丸子姐") == dummy_target
    # except CeobeCanteen.ParseTargetException as e:
    #     logger.error(e.prompt)
    #     pytest.fail("fuzzy search failed")
    with pytest.raises(CeobeCanteen.ParseTargetException) as pe1:
        await ceobecanteen.parse_target("丸子姐")

    assert pe1.value.prompt
    assert "Wan顽子-B站\nWan顽子-微博" in pe1.value.prompt

    with pytest.raises(CeobeCanteen.ParseTargetException) as pe2:
        await ceobecanteen.parse_target("明日方舟")

    assert pe2.value.prompt
    assert "明日方舟-B站" in pe2.value.prompt
