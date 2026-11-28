from httpx import Response
from nonebug.app import App
import pytest
import respx

from .utils import get_json

NEWS_LIST_URL = (
    "https://cqnews.web.sdo.com/api/news/newsList"
    "?gameCode=ff&CategoryCode=8324,8325,8326,8327,5309,5310,5311,5312,5313&pageIndex=0&pageSize=10"
)
NEWS_DETAIL_URL = "https://cqnews.web.sdo.com/api/news/newsDetail"


@pytest.fixture
def ff14(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    return platform_manager["ff14"](ProcessContext(DefaultClientManager()))


@pytest.fixture(scope="module")
def ff14_newdata_json_0():
    return get_json("ff14-newdata-0.json")


@pytest.fixture(scope="module")
def ff14_newdata_json_1():
    return get_json("ff14-newdata-1.json")


@pytest.fixture(scope="module")
def ff14_detail_json():
    return get_json("ff14-detail-396041.json")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(ff14, dummy_user_subinfo, ff14_newdata_json_0, ff14_newdata_json_1, ff14_detail_json):
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit, Target

    newdata = respx.get(NEWS_LIST_URL)
    newdata.mock(return_value=Response(200, json=ff14_newdata_json_0))
    detail = respx.get(NEWS_DETAIL_URL).mock(return_value=Response(200, json=ff14_detail_json))

    target = Target("")
    res = await ff14.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert newdata.called
    assert not detail.called
    assert len(res) == 0

    newdata.mock(return_value=Response(200, json=ff14_newdata_json_1))
    res = await ff14.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res) == 1
    post: Post = res[0][1][0]
    assert post.platform.name == "最终幻想XIV官方公告"
    # 维护公告原来不在抓取的分类里，这里顺带确认它被抓到了
    assert post.title == "《最终幻想14》12月1日全区全服更新维护公告"
    assert post.url == "https://ff.web.sdo.com/web8/index.html#/newstab/newscont/396041"
    assert post.nickname == "最终幻想XIV官方公告"
    # 列表接口给的 Summary 只有一句话，正文要另外请求详情接口
    assert detail.called
    assert detail.calls[0].request.url.params["id"] == "396041"
    assert "<p>" not in post.content
    assert post.content.startswith("亲爱的冒险者：")
    assert "预计维护时间：2026年12月1日13:00-12月3日13:00" in post.content
    assert post.content.endswith("《最终幻想14》运营团队")


@pytest.mark.asyncio
@respx.mock
async def test_detail_request_failed(ff14, ff14_newdata_json_0):
    "详情接口挂了也要把公告发出去，正文退回列表里的 Summary"
    respx.get(NEWS_DETAIL_URL).mock(return_value=Response(200, json={"Code": "0", "Data": {}}))

    raw_post = ff14_newdata_json_0["Data"][0]
    post = await ff14.parse(raw_post)

    assert post.content == raw_post["Summary"]


@pytest.mark.asyncio
@respx.mock
async def test_deleted_news_filtered(ff14):
    "官网把下架文章的 Summary 改成 333，这种条目不该当成公告发出去"
    from nonebot_bison.types import Target

    raw_data = get_json("ff14-newdata-0.json")
    deleted_id = raw_data["Data"][0]["Id"]
    raw_data["Data"][0]["Summary"] = "333"
    respx.get(NEWS_LIST_URL).mock(return_value=Response(200, json=raw_data))

    posts = await ff14.get_sub_list(Target(""))

    assert deleted_id not in [post["Id"] for post in posts]
    assert len(posts) == len(raw_data["Data"]) - 1
