import pytest
from nonebug import App


@pytest.mark.card
async def test_arknights_theme(app: App):
    from nonebot_bison.cards import card_manager

    ark = card_manager["arknights"]
    assert ark is not None
    assert ark.theme == "arknights"
    assert ark.render is not None
    assert ark.schemas is not None

    ark_card_data = ark.schemas.parse_obj(
        {"announce_title": "公告", "banner_image_url": "https://example.com/banner.jpg", "content": "<p>公告内容</p>"}
    )
    card = await ark.render(ark_card_data)
    assert isinstance(card, bytes)
