import pytest
from nonebug import App


@pytest.mark.asyncio
async def test_rss_has_url(app: App):
    from nonebot_bison.post.plain_post import PlainPost

    post = PlainPost(
        platform="rss",
        text="Nonebot Bison 通用的平台消息推送工具，励志做全泰拉骑自行车最快的信使",
        url="https://nonebot-bison.netlify.app/",
        target_name="rss-bison",
    )
    messages = await post._text_to_img()
    assert len(messages) == 2
