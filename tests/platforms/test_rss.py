import typing
import xml.etree.ElementTree as ET
from datetime import datetime

import pytest
import pytz
import respx
from httpx import AsyncClient, Response
from nonebug.app import App

from .utils import get_file

if typing.TYPE_CHECKING:
    from nonebot_bison.platform.rss import Rss


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
    from nonebot_bison.utils import ProcessContext

    return platform_manager["rss"](ProcessContext(), AsyncClient())


@pytest.fixture
def update_time_feed():
    file = get_file("rss-twitter-ArknightsStaff.xml")
    root = ET.fromstring(file)
    item = root.find("channel/item")
    current_time = datetime.now(pytz.timezone("GMT")).strftime(
        "%a, %d %b %Y %H:%M:%S %Z"
    )
    pubdate_elem = item.find("pubDate")
    pubdate_elem.text = current_time
    updated_xml = ET.tostring(root, encoding="unicode")
    return updated_xml


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(
    rss,
    user_info_factory,
    update_time_feed,
):
    rss_router = respx.get("https://rsshub.app/twitter/user/ArknightsStaff")
    rss_router.mock(
        return_value=Response(200, text=get_file("rss-twitter-ArknightsStaff-0.xml"))
    )
    target = "https://rsshub.app/twitter/user/ArknightsStaff"
    res1 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res1) == 0

    rss_router.mock(return_value=Response(200, text=update_time_feed))
    res2 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res2[0][1]) == 1
    post1 = res2[0][1][0]
    assert post1.url == "https://twitter.com/ArknightsStaff/status/1659091539023282178"
    assert (
        post1.text
        == "【#統合戦略】 引き続き新テーマ「ミヅキと紺碧の樹」の新要素及びシステムの変更点を一部ご紹介します！ 今回は「灯火」、「ダイス」、「記号認識」...\n【#統合戦略】 引き続き新テーマ「ミヅキと紺碧の樹」の新要素及びシステムの変更点を一部ご紹介します！ 今回は「灯火」、「ダイス」、「記号認識」、「鍵」についてです。詳細は添付の画像をご確認ください。#アークナイツ https://t.co/ARmptV0Zvu"
    )
