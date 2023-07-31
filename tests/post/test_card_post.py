import pytest
from nonebug import App


@pytest.mark.asyncio
async def test_card_post(app: App, fake_card, fake_render):
    from nonebot_plugin_saa import Image

    from nonebot_bison.post.card_post import CardPost
    from nonebot_bison.cards import ThemeMetadata, card_manager

    card_manager.register(ThemeMetadata(theme="test", render=fake_render, schemas=fake_card))

    post = CardPost(
        theme="test",
        card_data=fake_card(text="wow"),
    )
    messages = await post.generate()
    assert isinstance(messages[0], Image)
    assert messages[0].data.get("image") == await fake_render(fake_card(text="wow"))
