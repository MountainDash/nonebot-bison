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


@pytest.mark.asyncio
@pytest.mark.render
@respx.mock
async def test_javanews_parser(mcbbsnews, raw_post_list):
    javanews_mock = respx.get("https://www.mcbbs.net/thread-1338607-1-1.html")
    javanews_mock.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_javanews.html")
        )
    )
    raw_post = raw_post_list[3]
    post = await mcbbsnews.parse(raw_post)
    assert post.text == "{}\n│\n└由 {} 发表".format(raw_post["title"], raw_post["author"])
    assert post.target_name == raw_post["category"]
    assert len(post.pics) == 1


@pytest.mark.asyncio
@pytest.mark.render
@respx.mock
async def test_bedrocknews_parser(mcbbsnews, raw_post_list):
    bedrocknews_mock = respx.get("https://www.mcbbs.net/thread-1338592-1-1.html")
    bedrocknews_mock.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_bedrocknews.html")
        )
    )
    raw_post = raw_post_list[4]
    post = await mcbbsnews.parse(raw_post)
    assert post.text == "{}\n│\n└由 {} 发表".format(raw_post["title"], raw_post["author"])
    assert post.target_name == raw_post["category"]
    assert len(post.pics) == 1


@pytest.mark.asyncio
@pytest.mark.render
@respx.mock
async def test_bedrock_express_parser(mcbbsnews, raw_post_list):
    bedrock_express_mock = respx.get("https://www.mcbbs.net/thread-1332424-1-1.html")
    bedrock_express_mock.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_bedrock_express.html")
        )
    )
    raw_post = raw_post_list[13]
    post = await mcbbsnews.parse(raw_post)
    assert post.target_name == raw_post["category"]
    assert post.text == "{}\n│\n└由 {} 发表".format(raw_post["title"], raw_post["author"])


@pytest.mark.asyncio
@pytest.mark.render
@respx.mock
async def test_java_express_parser(mcbbsnews, raw_post_list):
    java_express_mock = respx.get("https://www.mcbbs.net/thread-1340080-1-1.html")
    java_express_mock.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_java_express.html")
        )
    )
    raw_post = raw_post_list[0]
    post = await mcbbsnews.parse(raw_post)
    assert post.target_name == raw_post["category"]
    assert post.text == "{}\n│\n└由 {} 发表".format(raw_post["title"], raw_post["author"])


@pytest.mark.asyncio
@pytest.mark.render
@respx.mock
async def test_merch_parser(mcbbsnews, raw_post_list):
    mc_merch_mock = respx.get("https://www.mcbbs.net/thread-1342236-1-1.html")
    mc_merch_mock.mock(
        return_value=Response(200, text=get_file("mcbbsnews/mock/mcbbsnews_merch.html"))
    )
    raw_post = raw_post_list[26]
    post = await mcbbsnews.parse(raw_post_list[26])
    assert post.target_name == raw_post["category"]
    assert post.text == "{}\n│\n└由 {} 发表".format(raw_post["title"], raw_post["author"])


@pytest.mark.asyncio
@pytest.mark.render
@respx.mock
async def test_fetch_new(mcbbsnews, dummy_user_subinfo):
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
    assert post.text == "Minecraft Java版 1.19-pre1 发布\n│\n└由 希铁石z 发表"
    assert post.url == "https://www.mcbbs.net/thread-1340927-1-1.html"
    assert post.target_name == "Java版资讯"


@pytest.mark.asyncio
@pytest.mark.render
@respx.mock
async def test_news_render(mcbbsnews, dummy_user_subinfo):
    new_post = respx.get("https://www.mcbbs.net/thread-1340927-1-1.html")
    new_post.mock(
        return_value=Response(
            200, text=get_file("mcbbsnews/mock/mcbbsnews_new_post_html.html")
        )
    )
    pics = await mcbbsnews._news_render(
        "https://www.mcbbs.net/thread-1340927-1-1.html", "#post_25849603"
    )
    assert len(pics) == 1

    pics_err_on_assert = await mcbbsnews._news_render("", "##post_25849603")
    assert len(pics_err_on_assert) == 2

    pics_err_on_other = await mcbbsnews._news_render(
        "https://www.mcbbs.net/thread-1340927-1-1.html", "#post_err"
    )
    assert len(pics_err_on_other) == 2
