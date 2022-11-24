import pytest
import respx
from httpx import AsyncClient, Response
from nonebug.app import App

from .utils import get_file, get_json


@pytest.fixture
def mcbbsnews(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import ProcessContext

    return platform_manager["mcbbsnews"](ProcessContext(), AsyncClient())


@pytest.fixture(scope="module")
def raw_post_list():
    return get_json("mcbbsnews/mcbbsnews_raw_post_list.json")


@pytest.fixture(scope="module")
def javanews_post_0():
    return get_file("mcbbsnews/post/mcbbsnews_java_post-0.txt")


@pytest.fixture(scope="module")
def javanews_post_1():
    return get_file("mcbbsnews/post/mcbbsnews_java_post-1.txt")


@pytest.fixture(scope="module")
def bedrocknews_post():
    return get_file("mcbbsnews/post/mcbbsnews_bedrock_post.txt")


@pytest.mark.asyncio
@respx.mock
async def test_javanews_parser(mcbbsnews, raw_post_list, javanews_post_0):
    javanews_mock = respx.get("https://www.mcbbs.net/thread-1338607-1-1.html")
    javanews_mock.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_javanews.html")
        )
    )

    post = await mcbbsnews.parse(raw_post_list[3])
    assert post.text == javanews_post_0


@pytest.mark.asyncio
@respx.mock
async def test_bedrocknews_parser(mcbbsnews, raw_post_list, bedrocknews_post):
    bedrocknews_mock = respx.get("https://www.mcbbs.net/thread-1338592-1-1.html")
    bedrocknews_mock.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_bedrocknews.html")
        )
    )

    post = await mcbbsnews.parse(raw_post_list[4])
    assert post.text == bedrocknews_post


@pytest.mark.asyncio
@respx.mock
async def test_bedrock_express_parser(mcbbsnews, raw_post_list):
    bedrock_express_mock = respx.get("https://www.mcbbs.net/thread-1332424-1-1.html")
    bedrock_express_mock.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_bedrock_express.html")
        )
    )

    bedrock_express_post = await mcbbsnews.parse(raw_post_list[13])
    assert bedrock_express_post.text == get_file(
        "mcbbsnews/post/mcbbsnews_bedrock_express_post.txt"
    )


@pytest.mark.asyncio
@respx.mock
async def test_java_express_parser(mcbbsnews, raw_post_list):
    java_express_mock = respx.get("https://www.mcbbs.net/thread-1340080-1-1.html")
    java_express_mock.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_java_express.html")
        )
    )

    java_express_post = await mcbbsnews.parse(raw_post_list[0])
    assert java_express_post.text == get_file(
        "mcbbsnews/post/mcbbsnews_java_express_post.txt"
    )


@pytest.mark.asyncio
@respx.mock
async def test_merch_parser(mcbbsnews, raw_post_list):
    mc_merch_mock = respx.get("https://www.mcbbs.net/thread-1342236-1-1.html")
    mc_merch_mock.mock(
        return_value=Response(200, text=get_file("mcbbsnews/mock/mcbbsnews_merch.html"))
    )

    mc_merch_post = await mcbbsnews.parse(raw_post_list[26])
    assert mc_merch_post.text == get_file("mcbbsnews/post/mcbbsnews_merch_post.txt")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(mcbbsnews, dummy_user_subinfo, javanews_post_1):
    news_router = respx.get("https://www.mcbbs.net/forum-news-1.html")
    news_router.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_post_list_html-0.html")
        )
    )
    new_post = respx.get("https://www.mcbbs.net/thread-1340927-1-1.html")
    new_post.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_new_post_html.html")
        )
    )
    target = ""
    res = await mcbbsnews.fetch_new_post(target, [dummy_user_subinfo])
    assert news_router.called
    assert len(res) == 0
    news_router.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_post_list_html-1.html")
        )
    )
    res = await mcbbsnews.fetch_new_post(target, [dummy_user_subinfo])
    assert news_router.called
    post = res[0][1][0]
    assert post.target_type == "MCBBS幻翼块讯"
    assert post.text == javanews_post_1
    assert post.url == "https://www.mcbbs.net/thread-1340927-1-1.html"
    assert post.target_name == "Java版本资讯"
