import pytest
from nonebug import App


@pytest.mark.asyncio
@pytest.mark.render
async def test_gen_pic_message(app: App):
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.post import Post
    from nonebot_bison.post.types import Card, CardHeader, CommonContent

    plugin_config.bison_use_pic = True

    header = CardHeader(face="quote.png", name="11", desc="111", platform="111")

    common = CommonContent(text="222")

    card = Card(header=header, type="common", content=common)

    card_msg_post = await Post(
        text="111", target_type="222", target_name="333", url="444", pics=[], card=card
    ).generate_pic_messages()

    plugin_config.bison_plain_pic_post = True

    plain_msg_post = await Post(
        text="111", target_type="222", target_name="333", url="444", pics=[], card=card
    ).generate_pic_messages()

    assert (card_pic := card_msg_post[0].data.get("file"))
    assert (plain_pic := plain_msg_post[0].data.get("file"))
    assert card_pic != plain_pic
