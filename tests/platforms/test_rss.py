from datetime import datetime
import typing
import xml.etree.ElementTree as ET

from httpx import Response
from nonebug.app import App
import pytest
import pytz
import respx

from .utils import get_file

if typing.TYPE_CHECKING:
    pass


@pytest.fixture
def dummy_user(app: App):
    from nonebot_bison.types import User

    user = User(123, "group")
    return user


@pytest.fixture
def user_info_factory(app: App, dummy_user):
    from nonebot_bison.types import UserSubInfo

    def _user_info(category_getter, tag_getter):
        return UserSubInfo(dummy_user, category_getter, tag_getter)

    return _user_info


@pytest.fixture
def rss(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    return platform_manager["rss"](ProcessContext(DefaultClientManager()))


@pytest.fixture
def update_time_feed_1():
    file = get_file("rss-twitter-ArknightsStaff.xml")
    root = ET.fromstring(file)
    item = root.find("channel/item")
    current_time = datetime.now(pytz.timezone("GMT")).strftime("%a, %d %b %Y %H:%M:%S %Z")
    assert item is not None
    pubdate_elem = item.find("pubDate")
    assert pubdate_elem is not None
    pubdate_elem.text = current_time
    return ET.tostring(root, encoding="unicode")


@pytest.fixture
def update_time_feed_2():
    file = get_file("rss-ruanyifeng.xml")
    root = ET.fromstring(file)
    current_time = datetime.now(pytz.timezone("GMT")).strftime("%a, %d %b %Y %H:%M:%S %Z")
    published_element = root.find(".//{*}published")
    assert published_element is not None
    published_element.text = current_time
    return ET.tostring(root, encoding="unicode")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_1(
    rss,
    user_info_factory,
    update_time_feed_1,
):
    from nonebot_bison.types import SubUnit, Target

    ## 标题重复的情况
    rss_router = respx.get("https://rsshub.app/twitter/user/ArknightsStaff")
    rss_router.mock(return_value=Response(200, text=get_file("rss-twitter-ArknightsStaff-0.xml")))
    target = Target("https://rsshub.app/twitter/user/ArknightsStaff")
    res1 = await rss.fetch_new_post(SubUnit(target, [user_info_factory([], [])]))
    assert len(res1) == 0

    rss_router.mock(return_value=Response(200, text=update_time_feed_1))
    res2 = await rss.fetch_new_post(SubUnit(target, [user_info_factory([], [])]))
    assert len(res2[0][1]) == 1
    post1 = res2[0][1][0]
    assert post1.url == "https://twitter.com/ArknightsStaff/status/1659091539023282178"
    assert post1.title is None
    assert (
        post1.content
        == "【#統合戦略】 <br />引き続き新テーマ「ミヅキと紺碧の樹」の新要素及びシステムの変更点を一部ご紹介します！ "
        "<br /><br />"
        "今回は「灯火」、「ダイス」、「記号認識」、「鍵」についてです。<br />詳細は添付の画像をご確認ください。"
        "<br /><br />"
        "#アークナイツ https://t.co/ARmptV0Zvu<br />"
        '<img src="https://pbs.twimg.com/media/FwZG9YAacAIXDw2?format=jpg&amp;name=orig" />'
    )
    plain_content = await post1.get_plain_content()
    assert (
        plain_content == "【#統合戦略】 \n"
        "引き続き新テーマ「ミヅキと紺碧の樹」の新要素及びシステムの変更点を一部ご紹介します！ \n\n"
        "今回は「灯火」、「ダイス」、「記号認識」、「鍵」についてです。\n"
        "詳細は添付の画像をご確認ください。\n\n"
        "#アークナイツ https://t.co/ARmptV0Zvu\n"
        "[图片]"
    )


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_2(
    rss,
    user_info_factory,
    update_time_feed_2,
):
    from nonebot_bison.types import SubUnit, Target

    ## 标题与正文不重复的情况
    rss_router = respx.get("https://www.ruanyifeng.com/blog/atom.xml")
    rss_router.mock(return_value=Response(200, text=get_file("rss-ruanyifeng-0.xml")))
    target = Target("https://www.ruanyifeng.com/blog/atom.xml")
    res1 = await rss.fetch_new_post(SubUnit(target, [user_info_factory([], [])]))
    assert len(res1) == 0

    rss_router.mock(return_value=Response(200, text=update_time_feed_2))
    res2 = await rss.fetch_new_post(SubUnit(target, [user_info_factory([], [])]))
    assert len(res2[0][1]) == 1
    post1 = res2[0][1][0]
    assert post1.url == "http://www.ruanyifeng.com/blog/2023/05/weekly-issue-255.html"
    assert post1.title == "科技爱好者周刊（第 255 期）：对待 AI 的正确态度"
    assert post1.content == "这里记录每周值得分享的科技内容，周五发布。..."


@pytest.fixture
def update_time_feed_3():
    file = get_file("rss-github-atom.xml")
    root = ET.fromstring(file)
    current_time = datetime.now(pytz.timezone("GMT")).strftime("%a, %d %b %Y %H:%M:%S %Z")
    published_element = root.findall(".//{*}updated")[1]
    published_element.text = current_time
    return ET.tostring(root, encoding="unicode")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_3(
    rss,
    user_info_factory,
    update_time_feed_3,
):
    from nonebot_bison.types import SubUnit, Target

    ## 只有<updated>没有<published>
    rss_router = respx.get("https://github.com/R3nzTheCodeGOD/R3nzSkin/releases.atom")
    rss_router.mock(return_value=Response(200, text=get_file("rss-github-atom-0.xml")))
    target = Target("https://github.com/R3nzTheCodeGOD/R3nzSkin/releases.atom")
    res1 = await rss.fetch_new_post(SubUnit(target, [user_info_factory([], [])]))
    assert len(res1) == 0

    rss_router.mock(return_value=Response(200, text=update_time_feed_3))
    res2 = await rss.fetch_new_post(SubUnit(target, [user_info_factory([], [])]))
    assert len(res2[0][1]) == 1
    post1 = res2[0][1][0]
    assert post1.url == "https://github.com/R3nzTheCodeGOD/R3nzSkin/releases/tag/v3.0.9"
    assert post1.title == "R3nzSkin"
    assert post1.content == "No content."


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_4(
    rss,
    user_info_factory,
):
    from nonebot_bison.types import SubUnit, Target

    ## 没有日期信息的情况
    rss_router = respx.get("https://rsshub.app/wallhaven/hot?limit=5")
    rss_router.mock(return_value=Response(200, text=get_file("rss-top5-old.xml")))
    target = Target("https://rsshub.app/wallhaven/hot?limit=5")
    res1 = await rss.fetch_new_post(SubUnit(target, [user_info_factory([], [])]))
    assert len(res1) == 0

    rss_router.mock(return_value=Response(200, text=get_file("rss-top5-new.xml")))
    res2 = await rss.fetch_new_post(SubUnit(target, [user_info_factory([], [])]))
    assert len(res2[0][1]) == 1
    post1 = res2[0][1][0]
    assert post1.url == "https://wallhaven.cc/w/85rjej"
    assert post1.content == '<img alt="loading" class="lazyload" src="https://th.wallhaven.cc/small/85/85rjej.jpg" />'
    plain_content = await post1.get_plain_content()
    assert plain_content == "[图片]"


def test_similar_text_process():
    from nonebot_bison.utils import text_similarity

    str1 = ""
    str2 = "xxxx"
    with pytest.raises(ValueError, match="The length of string can not be 0"):
        text_similarity(str1, str2)
    str1 = "xxxx"
    str2 = ""
    with pytest.raises(ValueError, match="The length of string can not be 0"):
        text_similarity(str1, str2)
    str1 = (
        "天使九局下被追平，米基-莫尼亚克(Mickey Moniak)超前安打拒绝剧本，天使7-6老虎；阿莱克-博姆（Alec"
        " Bohm）再见安打，费城人4-3金莺..."
    )
    str2 = (
        "天使九局下被追平，米基-莫尼亚克(Mickey Moniak)超前安打拒绝剧本，天使7-6老虎；阿莱克-博姆（Alec"
        " Bohm）再见安打，费城人4-3金莺；布兰登-洛维（Brandon Lowe）阳春炮，光芒4-1马林鱼；皮特-阿隆索(Pete Alonso)、"
        "丹尼尔-沃格尔巴克(Daniel Vogelbach)背靠背本垒打，大都会9-3扬基；吉田正尚（Masataka Yoshida）3安2打点，"
        "红袜7-1勇士；凯尔-塔克（Kyle Tucker）阳春炮，太空人4-3连胜游骑兵。"
    )
    res = text_similarity(str1, str2)
    assert res > 0.8
    str1 = "我爱你"
    str2 = "你爱我"
    res = text_similarity(str1, str2)
    assert res <= 0.8
