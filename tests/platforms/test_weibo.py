from datetime import datetime
import typing

import feedparser
from httpx import AsyncClient, Response
from nonebug.app import App
import pytest
from pytz import timezone
import respx

from .utils import get_file, get_json

if typing.TYPE_CHECKING:
    from nonebot_bison.platform.weibo import Weibo

image_cdn_router = respx.route(host__regex=r"wx\d.sinaimg.cn", path__startswith="/large/")


@pytest.fixture
def weibo(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    return platform_manager["weibo"](ProcessContext(DefaultClientManager()))


@pytest.fixture(scope="module")
def weibo_ak_list_1():
    return get_json("weibo_ak_list_1.json")


@pytest.mark.asyncio
@respx.mock
async def test_get_name(weibo):
    profile_router = respx.get("https://m.weibo.cn/api/container/getIndex?type=uid&value=6279793937")
    profile_router.mock(return_value=Response(200, json=get_json("weibo_ak_profile.json")))
    name = await weibo.get_target_name(AsyncClient(), "6279793937")
    assert name == "明日方舟Arknights"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(weibo, dummy_user_subinfo):
    from nonebot_bison.post import Post
    from nonebot_bison.types import SubUnit, Target

    ak_list_router = respx.get("https://m.weibo.cn/api/container/getIndex?containerid=1076036279793937")
    detail_router = respx.get("https://m.weibo.cn/statuses/extend?id=4649031014551911")
    ak_list_router.mock(return_value=Response(200, json=get_json("weibo_ak_list_0.json")))
    detail_router.mock(return_value=Response(200, text=get_file("weibo_detail_4649031014551911")))
    image_cdn_router.mock(Response(200, content=b""))
    target = Target("6279793937")
    res = await weibo.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert ak_list_router.called
    assert len(res) == 0
    assert not detail_router.called
    mock_data = get_json("weibo_ak_list_1.json")
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res2 = await weibo.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res2) == 0
    mock_data["data"]["cards"][1]["mblog"]["created_at"] = datetime.now(timezone("Asia/Shanghai")).strftime(
        "%a %b %d %H:%M:%S %z %Y"
    )
    ak_list_router.mock(return_value=Response(200, json=mock_data))
    res3 = await weibo.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res3[0][1]) == 1
    assert not detail_router.called
    post: Post = res3[0][1][0]
    assert post.platform.platform_name == "weibo"
    assert post.content == "#明日方舟#\nSideStory「沃伦姆德的薄暮」复刻现已开启！ "
    assert post.url == "https://weibo.com/6279793937/KkBtUx2dv"
    assert post.nickname == "明日方舟Arknights"
    assert post.images
    assert len(post.images) == 1


@pytest.mark.asyncio
@respx.mock
async def test_fetch_repost(weibo):
    repost_detail_router = respx.get("https://m.weibo.cn/statuses/extend?id=4645748019299849")
    repost_detail_router.mock(return_value=Response(200, text=get_file("weibo_detail_4645748019299849")))
    image_cdn_router.mock(Response(200, content=b""))
    raw_post = get_json("weibo_ak_list_1.json")["data"]["cards"][3]
    post = await weibo.parse(raw_post)
    # 正文
    assert post.content == (
        "恭喜@黄防护服黄 等10名用户获得【音律联觉主题黑胶礼盒各一套】。微博官方唯一抽奖工具"
        + "@微博抽奖平台 -高级版对本次抽奖进行监督，结果公正有效。公示链接：微博抽奖平台"
    )
    assert post.url == "https://weibo.com/6279793937/KktFEsjrO"
    assert post.nickname == "明日方舟Arknights"
    # 转发内容
    assert post.repost is not None
    repost = post.repost
    assert repost_detail_router.called
    assert repost.content == (
        "#明日方舟# #音律联觉#\n"
        "2021明日方舟音律联觉Ambience Synesthesia专场演出官方录播将于6月12日10:30正式上线，"
        "本次录播为大会员专享，相关信息可关注 网页链接( http://mrfz.biligame.com/yllj/ )\n\n"
        "一、音律联觉原声EP将于2021年6月12日正式上架塞壬唱片官网及网易云音乐，敬请期待。\n"
        "【歌曲列表】\n"
        "1. CanNot Wait For\n"
        "2. ManiFesto:\n"
        "3. 灯华梦踏\n"
        "4. 前航远歌\n\n"
        "二、【明日方舟·音律联觉】BILIBILI个性装扮套装即将上线，相关信息可关注明日方舟BILIBILI官方账号。\n\n"
        "三、明日方舟音律联觉主题黑胶礼盒现已上架，详情可关注“明日方舟朝陇山”。\n\n"
        "关注并转发本条微博，我们将通过@微博抽奖平台 抽取十位博士送出"
        "【音律联觉主题黑胶礼盒各一套】，将于6月12日开奖。\n"
        "开奖后奖品会在出货后寄出。 明日方舟Arknights的"
        "微博视频( https://video.weibo.com/show?fid=1034:4645779462357001 ) 抽奖详情"
    )
    assert repost.url == "https://weibo.com/6279793937/Kjc77D1jz"
    assert repost.nickname == "明日方舟Arknights"
    # 无转发微博
    raw_post_1 = get_json("weibo_ak_list_1.json")["data"]["cards"][0]
    post = await weibo.parse(raw_post_1)
    assert post.repost is None


@pytest.mark.asyncio
@respx.mock
async def test_video_cover(weibo):
    router = respx.get("https://m.weibo.cn/statuses/extend?id=4645748019299849")
    router.mock(return_value=Response(200, text=get_file("weibo_detail_4645748019299849")))
    image_cdn_router.mock(Response(200, content=b""))
    raw_post = get_json("weibo_ak_list_1.json")["data"]["cards"][0]
    post = await weibo.parse(raw_post)
    assert len(post.images) == 1
    raw_post = get_json("weibo_ak_list_1.json")["data"]["cards"][3]
    post = await weibo.parse(raw_post)
    assert len(post.repost.images) == 1
    raw_post = get_json("weibo_ak_list_0.json")["data"]["cards"][0]
    post = await weibo.parse(raw_post)
    assert len(post.images) == 1


@pytest.mark.asyncio
async def test_classification(weibo):
    mock_data = get_json("weibo_ak_list_1.json")
    tuwen = mock_data["data"]["cards"][1]
    retweet = mock_data["data"]["cards"][3]
    video = mock_data["data"]["cards"][0]
    mock_data_ys = get_json("weibo_ys_list_0.json")
    text = mock_data_ys["data"]["cards"][2]
    assert weibo.get_category(retweet) == 1
    assert weibo.get_category(video) == 2
    assert weibo.get_category(tuwen) == 3
    assert weibo.get_category(text) == 4


@pytest.mark.asyncio
@respx.mock
async def test_parse_long(weibo):
    detail_router = respx.get("https://m.weibo.cn/statuses/extend?id=4645748019299849")
    detail_router.mock(return_value=Response(200, text=get_file("weibo_detail_4645748019299849")))
    raw_post = get_json("weibo_ak_list_1.json")["data"]["cards"][0]
    post = await weibo.parse(raw_post)
    assert "全文" not in post.content
    assert detail_router.called


def test_tag(weibo, weibo_ak_list_1):
    raw_post = weibo_ak_list_1["data"]["cards"][0]
    assert weibo.get_tags(raw_post) == ["明日方舟", "音律联觉"]


@pytest.mark.asyncio
@pytest.mark.compare
async def test_rsshub_compare(weibo):
    from nonebot_bison.types import Target

    target = Target("6279793937")
    raw_posts = filter(weibo.filter_platform_custom, await weibo.get_sub_list(target))
    posts = []
    for raw_post in raw_posts:
        posts.append(await weibo.parse(raw_post))
    url_set = {x.url for x in posts}
    feedres = feedparser.parse("https://rsshub.app/weibo/user/6279793937")
    for entry in feedres.entries[:5]:
        # print(entry)
        assert entry.link in url_set


test_post = {
    "mblog": {
        "text": (
            '<a  href="https://m.weibo.cn/search?containerid=231522type%3D1%26t%3D10%26q%3D%23%E5%88%9A%E5%87%BA%E7%94%9F%E7%9A%84%E5%B0%8F%E7%BE%8A%E9%A9%BC%E9%95%BF%E5%95%A5%E6%A0%B7%23&extparam=%23%E5%88%9A%E5%87%BA%E7%94%9F%E7%9A%84%E5%B0%8F%E7%BE%8A%E9%A9%BC%E9%95%BF%E5%95%A5%E6%A0%B7%23&luicode=10000011&lfid=1076036003966749"'
            ' data-hide=""><span class="surl-text">#刚出生的小羊驼长啥样#</span></a> <br />小羊驼三三来也<span'
            ' class="url-icon"><img alt=[好喜欢]'
            ' src="https://h5.sinaimg.cn/m/emoticon/icon/lxh/lxh_haoxihuan-51860b62e6.png" style="width:1em;'
            ' height:1em;" /></span><br /><a '
            ' href="https://m.weibo.cn/p/index?extparam=%E5%B0%8F%E7%BE%8A%E9%A9%BC%E4%B8%89%E4%B8%89&containerid=1008085ae16d2046db677de1b8491d2b708597&luicode=10000011&lfid=1076036003966749"'
            " data-hide=\"\"><span class='url-icon'><img style='width: 1rem;height: 1rem'"
            " src='https://n.sinaimg.cn/photo/5213b46e/20180926/timeline_card_small_super_default.png'></span><span"
            ' class="surl-text">小羊驼三三</span></a> '
        ),
        "bid": "KnssqeqKK",
    }
}


def test_chaohua_tag(weibo):
    tags = weibo.get_tags(test_post)
    assert "刚出生的小羊驼长啥样" in tags
    assert "小羊驼三三超话" in tags


async def test_parse_target(weibo: "Weibo"):
    from nonebot_bison.platform.platform import Platform

    res = await weibo.parse_target("https://weibo.com/u/6441489862")
    assert res == "6441489862"
    res = await weibo.parse_target("weibo.com/u/6441489862")
    assert res == "6441489862"
    res = await weibo.parse_target("6441489862")
    assert res == "6441489862"
    with pytest.raises(Platform.ParseTargetException):
        await weibo.parse_target("https://weibo.com/arknights")


@respx.mock
async def test_get_cookie_name(weibo: "Weibo"):
    from nonebot_bison.platform.weibo import WeiboClientManager

    router = respx.get("https://m.weibo.cn/setup/nick/detail")
    router.mock(return_value=Response(200, json=get_json("weibo_get-cookie-name.json")))
    weibo_client_mgr = WeiboClientManager()
    name = await weibo_client_mgr.get_cookie_name("{}")
    assert name == "weibo: [suyiiyii]"
