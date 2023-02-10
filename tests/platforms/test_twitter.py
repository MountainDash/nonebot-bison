from typing import TYPE_CHECKING

import pytest
import respx
from nonebug import App

if TYPE_CHECKING:
    from nonebot_bison.platform.twitter import Twitter
    from nonebot_bison.types import Target, UserSubInfo


@pytest.fixture
def twitter(app: App) -> "Twitter":
    from httpx import AsyncClient
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.platform.twitter import Twitter
    from nonebot_bison.utils import ProcessContext

    _twitter = platform_manager["twitter"](ProcessContext(), AsyncClient())
    assert isinstance(_twitter, Twitter)
    return _twitter


@pytest.fixture(autouse=True)
def twitter_session_mock():
    """劫持 Twitter 的 session 获取请求"""
    from httpx import Response

    first_router = respx.post("https://api.twitter.com/1.1/guest/activate.json")
    first_cookies = {
        "guest_id": "v1%3A167600169283947245",
        "guest_id_ads": "v1%3A167600169283947245",
        "guest_id_marketing": "v1%3A167600169283947245",
        "personalization_id": '"v1_VDtHrDcOav78YhBjDc/2tw=="',
    }
    first_headers = [
        ("Set-Cookie", f"{key}={value}") for key, value in first_cookies.items()
    ]
    first_response = Response(
        200, text='{"guest_token":"1623894914756120576"}', headers=first_headers
    )
    first_router.mock(return_value=first_response)

    second_router = respx.get("https://twitter.com/i/js_inst?c_name=ui_metrics")
    second_headers = [
        (
            "Set-Cookie",
            "_twitter_sess=BAh7CSIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%250ASGFzaHsABjoKQHVzZWR7ADoPY3JlYXRlZF9hdGwrCJghjDmGAToMY3NyZl9p%250AZCIlMzNkMzEzMWEwNmQ5Y2JkZWVmZDliMmUxMTExOWM3ODE6B2lkIiU1NGZi%250ANTVlYjM0Zjk3MzQ2NzIyMmYwOTNiYjcxYzlmMA%253D%253D--c62d069e898ec4c8a1a3bab26284a31214f45285",
        )
    ]
    second_response = Response(200, headers=second_headers)
    second_router.mock(return_value=second_response)


@pytest.fixture(autouse=True)
def twitter_get_user():
    """劫持 Twitter 用户数据的获取"""
    from httpx import Response

    from tests.platforms.utils import get_json

    user_by_screen_name_router = respx.get(
        "https://twitter.com/i/api/graphql/hc-pka9A7gyS3xODIafnrQ/UserByScreenName"
    )
    user_by_screen_name_router.mock(
        return_value=Response(200, json=get_json("twitter/twitter_user.json"))
    )


@pytest.fixture(autouse=True)
def twitter_get_tweet_list():
    """劫持用户推文列表的获取"""
    from httpx import Response

    from tests.platforms.utils import get_json

    mock_json = get_json("twitter/twitter_tweet_list.json")
    post_router = respx.get(
        "https://twitter.com/i/api/graphql/t4wEKVulW4Mbv1P0kgxTEw/UserTweetsAndReplies"
    )
    post_router.mock(return_value=Response(200, json=mock_json))


@pytest.fixture()
def target() -> "Target":
    """获取 Twitter 用户名"""
    from nonebot_bison.types import Target

    return Target("Test")


@pytest.mark.asyncio
@respx.mock
async def test_session_initial(twitter: "Twitter"):
    """测试能否获取 Twitter 的访问 session"""
    from nonebot_bison.platform.twitter import TwitterUtils

    await TwitterUtils.reset_session(twitter.client, force=True)
    assert TwitterUtils._header["x-csrf-token"] is not None
    assert TwitterUtils._header["x-guest-token"] is not None
    assert TwitterUtils._cookie is not None
    assert TwitterUtils._cookie["_twitter_sess"] is not None


@pytest.mark.asyncio
@respx.mock
async def test_get_target_name(twitter: "Twitter", target: "Target"):
    """测试能否请求用户数据得到昵称 (screen name)"""
    nickname = await twitter.get_target_name(twitter.client, target)
    assert nickname == "лил псина"


@pytest.mark.asyncio
@respx.mock
async def test_get_user_id(twitter: "Twitter", target: "Target"):
    """测试能够请求用户数据得到用户 ID"""
    from httpx import AsyncClient
    from nonebot_bison.platform.twitter import TwitterUtils

    user_id = await TwitterUtils.get_user_id(AsyncClient(), target)
    assert user_id == 84696166


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(
    twitter: "Twitter", target: "Target", dummy_user_subinfo: "UserSubInfo"
):
    """测试推文列表的差异比对，修改了其中一则条目"""
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    from httpx import Response

    from tests.platforms.utils import get_file, get_json

    path = Path(__file__).parent / "static"

    mock_json = get_json("twitter/twitter_tweet_list.json")
    post_router = respx.get(
        "https://twitter.com/i/api/graphql/t4wEKVulW4Mbv1P0kgxTEw/UserTweetsAndReplies"
    )
    post_router.mock(return_value=Response(200, json=mock_json))

    result = await twitter.fetch_new_post(target, [dummy_user_subinfo])
    assert len(result) == 0

    pointer = mock_json["data"]["user"]["result"]["timeline"]["timeline"][
        "instructions"
    ][1]["entries"][4]["content"]["itemContent"]["tweet_results"]["result"]["legacy"]
    pointer["created_at"] = datetime.now(timezone(timedelta(0))).strftime(
        "%a %b %d %H:%M:%S %z %Y"
    )
    pointer["id_str"] = str(int(pointer["id_str"]) + 1)

    post_router.mock(return_value=Response(200, json=mock_json))
    result = await twitter.fetch_new_post(target, [dummy_user_subinfo])
    assert len(result) == 1

    post = result[0][1][0]
    assert post.target_type == "twitter"
    assert (
        post.text
        == "【#にじさんじ コトブキヤショップ】『にじさんじバレンタイン2023』の描き下ろしイラストを使った等身大パネルが2/14～3/20の期間中各店で展示されます！フチをカットした特別仕様となっております。この機会に是非ご来店ください！#愛園愛美 #海妹四葉 #笹木咲 #西園チグサ #町田ちま"
    )
    assert post.url == "https://twitter.com/i/web/status/1623954931911913474"
    assert post.target_name == "コトブキヤきなこ【公式】"
    assert len(post.pics) == 2


@pytest.mark.asyncio
@respx.mock
async def test_tags(twitter: "Twitter", target: "Target"):
    """测试推文获取标签"""
    result = (await twitter.get_sub_list(target))[4]
    tags = twitter.get_tags(result)
    assert tags == {"町田ちま", "西園チグサ", "笹木咲", "にじさんじ", "海妹四葉", "愛園愛美"}


@pytest.mark.asyncio
@respx.mock
async def test_category(twitter: "Twitter", target: "Target"):
    """测试推文获取分类"""
    result = (await twitter.get_sub_list(target))[4]
    cat = twitter.get_category(result)
    assert cat == 5


@pytest.mark.asyncio
async def test_parse_target(twitter: "Twitter", target: "Target"):
    """测试从 URL 中获取用户名"""
    from nonebot_bison.platform.platform import Platform

    assert await twitter.parse_target("ozx_x0") == "ozx_x0"
    assert await twitter.parse_target("https://twitter.com/ozx_x0") == "ozx_x0"
    assert await twitter.parse_target("https://mobile.twitter.com/ozx_x0") == "ozx_x0"
    assert (
        await twitter.parse_target(
            "https://mobile.twitter.com/ozx_x0/status/1619978348872212480"
        )
        == "ozx_x0"
    )
    with pytest.raises(Platform.ParseTargetException):
        await twitter.parse_target("https://twitter.com/i/status/1485063511273181184")
