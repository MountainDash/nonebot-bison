import pytest
from nonebug.app import App


@pytest.mark.asyncio
@pytest.mark.render
async def test_plain_pic_render(app: App):
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.utils import parse_text

    plugin_config.bison_use_pic = True

    res = await parse_text(
        """a\nbbbbbbbbbbbbbbbbbbbbbb\ncd
<h1>中文</h1>
VuePress 由两部分组成：第一部分是一个极简静态网站生成器

(opens new window)，它包含由 Vue 驱动的主题系统和插件 API，另一个部分是为书写技术文档而优化的默认主题，它的诞生初衷是为了支持 Vue 及其子项目的文档需求。

每一个由 VuePress 生成的页面都带有预渲染好的 HTML，也因此具有非常好的加载性能和搜索引擎优化（SEO）。同时，一旦页面被加载，Vue 将接管这些静态内容，并将其转换成一个完整的单页应用（SPA），其他的页面则会只在用户浏览到的时候才按需加载。
"""
    )
    assert res.type == "image"


@pytest.mark.asyncio
@pytest.mark.render
async def test_common_card_render(app: App):
    from nonebot_bison.post.types import Card, CardHeader, CommonContent
    from nonebot_bison.post.utils import card_render

    content = CommonContent(
        text="<p>克丽斯腾平时可是很忙的！我想就算在月亮上也不例外吧。而且她从来不会好好打扮，不会准备演讲稿，不会在意其他同事们正在做的事情……我……我们会再见到她的。嗯。她还欠我很多东西呢。<p>"
    )
    header = CardHeader(
        face="quote.png", name="缪尔赛思", desc="泰拉历 xxxx-yy-zz hh:mm:ss", platform="TBS"
    )
    card = Card(type="common", header=header, content=content)

    res = await card_render(card)
    assert res.type == "image"


@pytest.mark.asyncio
@pytest.mark.render
async def test_video_card_render(app: App):
    from nonebot_bison.post.types import Card, CardHeader, VideoContent
    from nonebot_bison.post.utils import card_render

    content = VideoContent(
        text="特里蒙晚间电波秀",
        cover="quote.png",
        title="莱茵生命生态科主任独家访谈",
        brief="继“特里蒙弧光事件”后首次发声，莱茵生命生态科主任缪尔赛思解密泰拉天空！",
        category="科技",
    )

    header = CardHeader(
        face="quote.png", name="缪尔赛思", desc="泰拉历 xxxx-yy-zz hh:mm:ss", platform="TBS"
    )

    card = Card(type="video", header=header, content=content)

    res = await card_render(card)
    assert res.type == "image"


@pytest.mark.asyncio
@pytest.mark.render
async def test_repost_card_render(app: App):
    from nonebot_bison.post.types import Card, CardHeader, RepostContent, VideoContent
    from nonebot_bison.post.utils import card_render

    repost_content = VideoContent(
        text="特里蒙晚间电波秀",
        cover="quote.png",
        title="莱茵生命生态科主任独家访谈",
        brief="继“特里蒙弧光事件”后首次发声，莱茵生命生态科主任缪尔赛思解密泰拉天空！",
        category="科技",
    )
    repost_header = CardHeader(
        face="quote.png", name="缪尔赛思", desc="泰拉历 xxxx-yy-zz hh:mm:ss", platform="TBS"
    )
    repost = Card(type="video", header=repost_header, content=repost_content)

    content = RepostContent(text="特里蒙晚间电波秀记得看哦!", repost=repost)

    card = Card(type="repost", header=repost_header, content=content)

    res = await card_render(card)
    assert res.type == "image"


@pytest.mark.asyncio
@pytest.mark.render
async def test_live_card_render(app: App):
    from nonebot_bison.post.types import Card, CardHeader, LiveContent
    from nonebot_bison.post.utils import card_render

    content = LiveContent(
        text="特里蒙晚间电波秀",
        cover="quote.png",
    )

    header = CardHeader(
        face="quote.png", name="缪尔赛思", desc="泰拉历 xxxx-yy-zz hh:mm:ss", platform="TBS"
    )

    card = Card(type="live", header=header, content=content)

    res = await card_render(card)
    from .utils import show_pic

    show_pic(res.data["file"])
    assert res.type == "image"
