import typing
from datetime import datetime

import respx
import pytest
from httpx import Response
from nonebug.app import App
from nonebot.compat import model_dump, type_validate_python

from .utils import get_json


@pytest.fixture()
def bing_dy_list(app: App):
    from nonebot_bison.platform.bilibili.models import PostAPI

    return type_validate_python(PostAPI, get_json("bilibili-new.json")).data.items  # type: ignore


if typing.TYPE_CHECKING:
    from nonebot_bison.platform.bilibili import Bilibili


@pytest.fixture()
def bilibili(app: App) -> "Bilibili":
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import ProcessContext, DefaultClientManager

    return platform_manager["bilibili"](ProcessContext(DefaultClientManager()))  # type: ignore


@pytest.fixture()
def without_dynamic(app: App):
    from nonebot_bison.platform.bilibili.models import PostAPI

    # 先验证实际的空动态返回能否通过校验，再重新导出
    return model_dump(
        type_validate_python(
            PostAPI,
            {
                "code": 0,
                "ttl": 1,
                "message": "",
                "data": {
                    "items": None,
                    "has_more": 0,
                    "next_offset": 0,
                    "_gt_": 0,
                },
            },
        )
    )


@pytest.mark.asyncio
async def test_parser(bilibili: "Bilibili"):
    from nonebot_bison.platform.bilibili.models import PostAPI, UnknownMajor

    test_data = get_json("bilibili-new.json")
    res = type_validate_python(PostAPI, test_data)
    assert res.data is not None
    for item in res.data.items or []:
        assert item.modules
        assert not isinstance(item.modules.module_dynamic.major, UnknownMajor)


@pytest.mark.asyncio
async def test_get_tag(bilibili: "Bilibili", bing_dy_list):
    from nonebot_bison.platform.bilibili.models import DynRawPost

    raw_post_has_tag = type_validate_python(DynRawPost, bing_dy_list[6])

    res1 = bilibili.get_tags(raw_post_has_tag)
    assert set(res1) == {"明日方舟", "123罗德岛！？"}


async def test_dynamic_forward(bilibili: "Bilibili", bing_dy_list: list):
    from nonebot_bison.post import Post

    post: Post = await bilibili.parse(bing_dy_list[7])
    assert post.content == (
        "「2024明日方舟音律联觉-不觅浪尘」将于12:00正式开启预售票！预售票购票链接：https://m.damai.cn/shows/item.html?itemId=778626949623"
    )
    assert post.url == "https://t.bilibili.com/917092495452536836"
    assert (rp := post.repost)
    assert rp.content == (
        "互动抽奖 #明日方舟##音律联觉#\n\n"
        "「2024音律联觉」票务信息公开！\n\n\n\n"
        "「2024明日方舟音律联觉-不觅浪尘」将于【4月6日12:00】正式开启预售票，预售票购票链接："
        "https://m.damai.cn/shows/item.html?itemId=778626949623\n\n"
        "【活动地点】\n\n"
        "上海久事体育旗忠网球中心主场馆（上海市闵行区元江路5500弄）\n\n"
        "【活动时间】\n\n「不觅浪尘-日场」：5月1日-5月2日\\u0026"
        "5月4日-5月5日 13:00\n\n"
        "「不觅浪尘-夜场」：5月1日-5月2日\\u00265月4日-5月5日 18:30\n\n"
        "【温馨提醒】\n\n"
        "*「2024明日方舟音律联觉-不觅浪尘」演出共计4天，每天有日场和夜场各1场演出，共计8场次，每场演出为相同内容。\n\n"
        "*「2024明日方舟音律联觉-不觅浪尘」演出全部录播内容后续将于bilibili独家上线，敬请期待。\n\n"
        "*  音律联觉将为博士们准备活动场馆往返莘庄、北桥地铁站的免费接驳车，"
        "有需要乘坐的博士请合理安排自己的出行时间。\n\n"
        "【票务相关】\n\n"
        "* 本次票务和大麦网 进行合作，应相关要求本次预售仅预先开放70%的票量，"
        "剩余票量的开票时间请继续关注明日方舟官方自媒体账号的后续通知。\n\n"
        "* 预售期间，由于未正式开票，下单后无法立即为您配票，待正式开票后，您可通过订单详情页或票夹详情，"
        "查看票品信息。\n\n* 本次演出为非选座电子票，依照您的付款时间顺序出票，如果您同一订单下购买多张票，"
        "正式开票后，系统将会优先为您选择相连座位。\n\n\n"
        "更多详情可查看下方长图，或查看活动详情页：https://ak.hypergryph.com/special/amb-2024/ \n\n\n\n"
        "* 请各位购票前务必确认票档和相关购票须知，并提前在对应票务平台后台添加完整的个人购票信息，以方便购票。\n\n"
        "* 明日方舟嘉年华及音律联觉活动场地存在一定距离，且活动时间有部分重叠，推荐都参加的博士选择不同日期购票。\n\n"
        "\n\n关注并转发本动态，我们将会在5月6日抽取20位博士各赠送【2024音律联觉主题亚克力画（随机一款）】一份。"
        "中奖的幸运博士请于开奖后5日内提交获奖信息，逾期视为自动放弃奖励。"
    )
    assert rp.images
    assert len(rp.images) == 9
    assert rp.url == "https://t.bilibili.com/915793667264872453"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_without_dynamic(bilibili, dummy_user_subinfo, without_dynamic):
    from nonebot_bison.types import Target, SubUnit

    target = Target("161775300")
    post_router = respx.get(
        f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={target}&timezone_offset=-480&offset="
    )
    post_router.mock(return_value=Response(200, json=without_dynamic))
    res = await bilibili.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert post_router.called
    assert len(res) == 0


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new(bilibili, dummy_user_subinfo):
    from nonebot.compat import model_dump, type_validate_python

    from nonebot_bison.types import Target, SubUnit
    from nonebot_bison.platform.bilibili.models import PostAPI

    target = Target("161775300")

    post_router = respx.get(
        f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={target}&timezone_offset=-480&offset="
    )
    post_list = type_validate_python(PostAPI, get_json("bilibili-new.json"))
    assert post_list.data
    assert post_list.data.items
    post_0 = post_list.data.items.pop(0)
    post_router.mock(return_value=Response(200, json=model_dump(post_list)))

    res = await bilibili.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert post_router.called
    assert len(res) == 0

    post_0.modules.module_author.pub_ts = int(datetime.now().timestamp())
    post_list.data.items.insert(0, post_0)
    post_router.mock(return_value=Response(200, json=model_dump(post_list)))
    res2 = await bilibili.fetch_new_post(SubUnit(target, [dummy_user_subinfo]))
    assert len(res2[0][1]) == 1
    post = res2[0][1][0]
    assert post.content == (
        "SideStory「巴别塔」限时活动即将开启\n\n\n\n"
        "一、全新SideStory「巴别塔」，活动关卡开启\n\n"
        "二、【如死亦终】限时寻访开启\n\n"
        "三、新干员登场，信赖获取提升\n\n"
        "四、【时代】系列，新装限时上架\n\n"
        "五、复刻时装限时上架\n\n"
        "六、新增【“疤痕商场的回忆”】主题家具，限时获取\n\n"
        "七、礼包限时上架\n\n"
        "八、【前路回响】限时寻访开启\n\n"
        "九、【玛尔特】系列，限时复刻上架\n\n\n\n"
        "更多活动内容请持续关注《明日方舟》游戏内公告及官方公告。"
    )


async def test_parse_target(bilibili: "Bilibili"):
    from nonebot_bison.platform.platform import Platform

    res = await bilibili.parse_target(
        "https://space.bilibili.com/161775300?from=search&seid=130517740606234234234&spm_id_from=333.337.0.0"
    )
    assert res == "161775300"
    res2 = await bilibili.parse_target(
        "space.bilibili.com/161775300?from=search&seid=130517740606234234234&spm_id_from=333.337.0.0"
    )
    assert res2 == "161775300"
    with pytest.raises(Platform.ParseTargetException):
        await bilibili.parse_target("https://www.bilibili.com/video/BV1qP4y1g738?spm_id_from=333.999.0.0")
