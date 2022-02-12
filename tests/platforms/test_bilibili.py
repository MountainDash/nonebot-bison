import pytest
from httpx import Response
from nonebug.app import App

from .utils import get_json


@pytest.fixture(scope="module")
def bing_dy_list():
    return get_json("bilibili_bing_list.json")["data"]["cards"]


@pytest.fixture
def bilibili(app: App):
    from nonebot_bison.platform import platform_manager

    return platform_manager["bilibili"]


@pytest.mark.asyncio
async def test_video_forward(bilibili, bing_dy_list):
    post = await bilibili.parse(bing_dy_list[1])
    assert (
        post.text
        == "答案揭晓：宿舍！来看看投票结果\nhttps://t.bilibili.com/568093580488553786\n--------------\n#可露希尔的秘密档案# \n11：来宿舍休息一下吧 \n档案来源：lambda:\\罗德岛内务\\秘密档案 \n发布时间：9/12 1:00 P.M. \n档案类型：可见 \n档案描述：今天请了病假在宿舍休息。很舒适。 \n提供者：赫默"
    )


@pytest.mark.asyncio
async def test_article_forward(bilibili, bing_dy_list):
    post = await bilibili.parse(bing_dy_list[4])
    assert (
        post.text
        == "#明日方舟##饼学大厦#\n9.11专栏更新完毕，这还塌了实属没跟新运营对上\n后边除了周日发饼和PV没提及的中文语音，稳了\n别忘了来参加#可露希尔的秘密档案#的主题投票\nhttps://t.bilibili.com/568093580488553786?tab=2"
        + "\n--------------\n"
        + "【明日方舟】饼学大厦#12~14（风暴瞭望&玛莉娅·临光&红松林&感谢庆典）9.11更新 更新记录09.11更新：覆盖09.10更新；以及排期更新，猜测周一周五开活动09.10更新：以周五开活动为底，PV/公告调整位置，整体结构更新09.08更新：饼学大厦#12更新，新增一件六星商店服饰（周日发饼）09.06更新：饼学大厦整栋整栋翻新，改为9.16开主线（四日无饼！）09.05凌晨更新：10.13后的排期（两日无饼，鹰角背刺，心狠手辣）前言感谢楪筱祈ぺ的动态-哔哩哔哩 (bilibili.com) 对饼学的贡献！后续排期：9.17【风暴瞭望】、10.01【玛莉娅·临光】复刻、10.1"
    )


@pytest.mark.asyncio
async def test_dynamic_forward(bilibili, bing_dy_list):
    post = await bilibili.parse(bing_dy_list[5])
    assert (
        post.text
        == "饼组主线饼学预测——9.11版\n①今日结果\n9.11 殿堂上的游禽-星极(x，新运营实锤了)\n②后续预测\n9.12 #罗德岛相簿#+#可露希尔的秘密档案#11话\n9.13 六星先锋(执旗手)干员-琴柳\n9.14 宣传策略-空弦+家具\n9.15 轮换池（+中文语音前瞻）\n9.16 停机\n9.17 #罗德岛闲逛部#+新六星EP+EP09·风暴瞭望开启\n9.19 #罗德岛相簿#"
        + "\n--------------\n"
        + "#明日方舟#\n【新增服饰】\n//殿堂上的游禽 - 星极\n塞壬唱片偶像企划《闪耀阶梯》特供服饰/殿堂上的游禽。星极自费参加了这项企划，尝试着用大众能接受的方式演绎天空之上的故事。\n\n_____________\n谦逊留给观众，骄傲发自歌喉，此夜，唯我璀璨。 "
    )
