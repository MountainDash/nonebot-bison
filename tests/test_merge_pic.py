import typing

import pytest
from flaky import flaky
from nonebug.app import App

if typing.TYPE_CHECKING:
    import sys

    sys.path.append("./src/plugins")
    import nonebot_bison

merge_source_9 = [
    "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vib7zooj30dx0dxmz5.jpg",
    "https://wx4.sinaimg.cn/large/0071VPLMgy1gq0vib5oqjj30dw0dxjt2.jpg",
    "https://wx2.sinaimg.cn/large/0071VPLMgy1gq0vib8bjmj30dv0dxgn7.jpg",
    "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vib6pn1j30dx0dw75v.jpg",
    "https://wx4.sinaimg.cn/large/0071VPLMgy1gq0vib925mj30dw0dwabb.jpg",
    "https://wx2.sinaimg.cn/large/0071VPLMgy1gq0vib7ujuj30dv0dwtap.jpg",
    "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vibaexnj30dx0dvq49.jpg",
    "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vibehw4j30dw0dv74u.jpg",
    "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vibfb5fj30dv0dvtac.jpg",
    "https://wx3.sinaimg.cn/large/0071VPLMgy1gq0viexkjxj30rs3pcx6p.jpg",
    "https://wx2.sinaimg.cn/large/0071VPLMgy1gq0vif6qrpj30rs4mou10.jpg",
    "https://wx4.sinaimg.cn/large/0071VPLMgy1gq0vifc826j30rs4a64qs.jpg",
    "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vify21lj30rsbj71ld.jpg",
]
merge_source_9_2 = [
    "https://wx2.sinaimg.cn/large/0071VPLMgy1gxo0eyycd7j30dw0dd3zk.jpg",
    "https://wx1.sinaimg.cn/large/0071VPLMgy1gxo0eyx6mhj30dw0ddjs8.jpg",
    "https://wx4.sinaimg.cn/large/0071VPLMgy1gxo0eyxf2bj30dw0dddh4.jpg",
    "https://wx3.sinaimg.cn/large/0071VPLMgy1gxo0ez1h5zj30dw0efwfs.jpg",
    "https://wx3.sinaimg.cn/large/0071VPLMgy1gxo0eyyku4j30dw0ef3zm.jpg",
    "https://wx1.sinaimg.cn/large/0071VPLMgy1gxo0ez0bjhj30dw0efabs.jpg",
    "https://wx4.sinaimg.cn/large/0071VPLMgy1gxo0ezdcafj30dw0dwacb.jpg",
    "https://wx1.sinaimg.cn/large/0071VPLMgy1gxo0ezg2g3j30dw0dwq51.jpg",
    "https://wx3.sinaimg.cn/large/0071VPLMgy1gxo0ez5oloj30dw0dw0uf.jpg",
    "https://wx4.sinaimg.cn/large/0071VPLMgy1gxo0fnk6stj30rs44ne81.jpg",
    "https://wx2.sinaimg.cn/large/0071VPLMgy1gxo0fohgcoj30rs3wpe81.jpg",
    "https://wx3.sinaimg.cn/large/0071VPLMgy1gxo0fpr6chj30rs3m1b29.jpg",
]


@flaky
async def test_9_merge(app: App):
    from nonebot_bison.post import Post

    post = Post("", "", "", pics=merge_source_9)
    await post._pic_merge()
    assert len(post.pics) == 5
    await post.generate_messages()


@flaky
async def test_9_merge_2(app: App):
    from nonebot_bison.post import Post

    post = Post("", "", "", pics=merge_source_9_2)
    await post._pic_merge()
    assert len(post.pics) == 4
    await post.generate_messages()


@flaky
async def test_6_merge(app: App):
    from nonebot_bison.post import Post

    post = Post("", "", "", pics=merge_source_9[0:6] + merge_source_9[9:])
    await post._pic_merge()
    assert len(post.pics) == 5


@flaky
async def test_3_merge(app: App):
    from nonebot_bison.post import Post

    post = Post("", "", "", pics=merge_source_9[0:3] + merge_source_9[9:])
    await post._pic_merge()
    assert len(post.pics) == 5


@flaky
async def test_6_merge_only(app: App):
    from nonebot_bison.post import Post

    post = Post("", "", "", pics=merge_source_9[0:6])
    await post._pic_merge()
    assert len(post.pics) == 1


@flaky
async def test_3_merge_only(app: App):
    from nonebot_bison.post import Post

    post = Post("", "", "", pics=merge_source_9[0:3])
    await post._pic_merge()
    assert len(post.pics) == 1
