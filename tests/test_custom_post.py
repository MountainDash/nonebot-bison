import pytest
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot_bison.post import custom_post
from nonebug.app import App


@pytest.fixture
def expect_md():
    return "【Zc】每早合约日替攻略！\n![Iamge](http://i0.hdslb.com/bfs/live/new_room_cover/cf7d4d3b2f336c6dba299644c3af952c5db82612.jpg)\n来源: Bilibili直播 魔法Zc目录\n\n详情: https://live.bilibili.com/3044248\n"


def test_gene_md(app: App):

    msg_segments: list[MessageSegment] = []
    msg_segments.append(MessageSegment.text("【Zc】每早合约日替攻略！"))
    msg_segments.append(
        MessageSegment.image(
            file="http://i0.hdslb.com/bfs/live/new_room_cover/cf7d4d3b2f336c6dba299644c3af952c5db82612.jpg",
            cache=0,
        )
    )
    msg_segments.append(MessageSegment.text("来源: Bilibili直播 魔法Zc目录\n "))
    msg_segments.append(MessageSegment.text("详情: https://live.bilibili.com/3044248"))

    cp = custom_post.CustomPost(message_segments=msg_segments)
    cp_md = cp._generate_md()

    assert cp_md == expect_md()
