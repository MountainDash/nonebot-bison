import pytest
from nonebug import App
from pydantic import BaseModel


@pytest.fixture(scope="module")
def fake_card():
    class FakeCard(BaseModel):
        text: str

    return FakeCard


@pytest.fixture(scope="module")
def fake_render():
    async def fake_render_func(x: str) -> str:
        return x

    return fake_render_func


@pytest.mark.asyncio
async def test_meta_class(app: App, fake_card, fake_render):
    from nonebot_bison.cards import ThemeMetadata

    test_meta = ThemeMetadata(
        theme="test",
        render=fake_render,
        schemas=fake_card,
    )

    assert test_meta.theme == "test"
    assert test_meta.render == fake_render
    assert test_meta.schemas == fake_card

    assert await test_meta.render("test") == "test"
    assert test_meta.schemas(text="test").__fields_set__ == {"text"}


@pytest.mark.asyncio
async def test_card_manager(app: App, fake_card, fake_render):
    from nonebot_bison.cards.registry import CardManager, ThemeMetadata

    test_meta = ThemeMetadata(
        theme="test",
        render=fake_render,
        schemas=fake_card,
    )

    fake_card_manager = CardManager()
    fake_card_manager.register(test_meta)

    assert fake_card_manager["test"] == test_meta
    assert await fake_card_manager["test"].render("test") == "test"
    assert fake_card_manager["test"].schemas(text="test").__fields_set__ == {"text"}


@pytest.mark.asyncio
async def test_cards_load(app: App):
    from nonebot_bison import cards

    assert len(cards.card_manager) == (3 + 1)  # 加上一个test
    assert "bison" in cards.card_manager
    assert isinstance(cards.card_manager["bison"], cards.registry.ThemeMetadata)
