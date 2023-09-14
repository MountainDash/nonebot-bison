from typing import TYPE_CHECKING

import respx
import pytest
from flaky import flaky
from nonebug.app import App
from httpx import Response, AsyncClient

from .utils import get_file, get_json

if TYPE_CHECKING:
    from nonebot_bison.platform.mcbbsnews import McbbsNews


@pytest.fixture()
def mcbbsnews(app: App):
    from nonebot_bison.utils import ProcessContext
    from nonebot_bison.platform import platform_manager

    return platform_manager["mcbbsnews"](ProcessContext(), AsyncClient())


@pytest.fixture(scope="module")
def raw_post_list():
    return get_json("mcbbsnews/mcbbsnews_raw_post_list_update.json")


@pytest.mark.asyncio
@pytest.mark.render
@respx.mock
@flaky(max_runs=3, min_passes=1)
async def test_fetch_new(mcbbsnews: "McbbsNews", dummy_user_subinfo, raw_post_list):
    from nonebot_bison.card.themes import PlainStem
    from nonebot_bison.types import Target, SubUnit

    news_router = respx.get("https://www.mcbbs.net/forum-news-1.html")
    news_router.mock(return_value=Response(200, text=get_file("mcbbsnews/mock/mcbbsnews_post_list_html-0.html")))
    new_post = respx.get("https://www.mcbbs.net/thread-1340927-1-1.html")
    new_post.mock(return_value=Response(200, text=get_file("mcbbsnews/mock/mcbbsnews_new_post_html.html")))
    target = Target("")
    res = await mcbbsnews.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert news_router.called
    assert len(res) == 0

    news_router.mock(return_value=Response(200, text=get_file("mcbbsnews/mock/mcbbsnews_post_list_html-1.html")))
    res2 = await mcbbsnews.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert news_router.called
    post2 = res2[0][1][0]
    raw_post = raw_post_list[0]
    assert isinstance(post2.card_data, PlainStem)
    assert post2.card_data.platform == "MCBBS幻翼块讯"
    assert post2.card_data.text == "{}\n│\n└由 {} 发表".format(raw_post["title"], raw_post["author"])
    assert post2.card_data.url == "https://www.mcbbs.net/{}".format(raw_post["url"])
    assert post2.card_data.target_name == raw_post["category"]
    assert len(post2.pics) == 1


@pytest.mark.asyncio
@pytest.mark.render
@respx.mock
@flaky(max_runs=3, min_passes=1)
async def test_news_render(mcbbsnews, dummy_user_subinfo):
    new_post = respx.get("https://www.mcbbs.net/thread-1340927-1-1.html")
    new_post.mock(return_value=Response(200, text=get_file("mcbbsnews/mock/mcbbsnews_new_post_html.html")))
    pics = await mcbbsnews._news_render("https://www.mcbbs.net/thread-1340927-1-1.html", "#post_25849603")
    assert len(pics) == 1

    pics_err_on_assert = await mcbbsnews._news_render("", "##post_25849603")
    assert len(pics_err_on_assert) == 2

    pics_err_on_other = await mcbbsnews._news_render("https://www.mcbbs.net/thread-1340927-1-1.html", "#post_err")
    assert len(pics_err_on_other) == 2
