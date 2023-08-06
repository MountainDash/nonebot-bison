import pytest
from nonebug import App


@pytest.mark.card
async def test_ceobe_theme(app: App):
    from nonebot_bison.cards import card_manager
    from nonebot_bison.cards.themes.ceobe_canteen.schemas import Card

    ceobe = card_manager["ceobecanteen"]
    assert ceobe is not None
    assert ceobe.theme == "ceobecanteen"
    assert ceobe.render is not None
    assert ceobe.schemas is not None

    card_data = ceobe.schemas.parse_obj(
        {
            "info": {
                "datasource": "测试数据源",
                "time": "2021-10-01 00:00:00",
            },
            "content": {
                "image": "https://example.com/example.jpg",
                "text": "测试文字",
            },
            "qr": "https://example.com/",
        }
    )
    assert isinstance(card_data, Card)
    assert card_data.info.datasource == "测试数据源"
    assert card_data.info.time == "2021-10-01 00:00:00"
    assert card_data.content.image == "https://example.com/example.jpg"
    assert card_data.content.text == "测试文字"
    assert card_data.qr != "https://example.com/"
    assert card_data.qr.startswith("<svg")
    card = await ceobe.render(card_data)
    assert isinstance(card, bytes)
