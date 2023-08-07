import pytest
from nonebug import App


@pytest.mark.asyncio
async def test_base_post(app: App):
    from nonebot_plugin_saa import Text

    from nonebot_bison.post.plain_post import BasePost

    post = BasePost(
        platform="rss",
        text="Nonebot Bison 通用的平台消息推送工具，励志做全泰拉骑自行车最快的信使",
        url="https://nonebot-bison.netlify.app/",
        target_name="rss-bison",
    )
    messages = await post.generate()
    assert isinstance(messages[0], Text)


@pytest.mark.asyncio
async def test_plain_post(app: App):
    from nonebot_plugin_saa import Text, Image

    from nonebot_bison import plugin_config
    from nonebot_bison.post.plain_post import PlainPost

    plugin_config.bison_use_pic = True

    # 顺便测试rss的url不被忽略
    post = PlainPost(
        platform="rss",
        text="Nonebot Bison 通用的平台消息推送工具，励志做全泰拉骑自行车最快的信使",
        url="https://nonebot-bison.netlify.app/",
        target_name="rss-bison",
    )
    messages = await post.generate()
    assert isinstance(messages, list)
    assert isinstance(messages[0], Image)
    assert len(messages) == 2

    plugin_config.bison_use_pic = False
    messages2 = await post.generate()
    assert isinstance(messages2[0], Text)
