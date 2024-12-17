from typing import Literal

from nonebug import App
import pytest


@pytest.mark.asyncio
async def test_registry_new_theme(app: App):
    from nonebot_bison.theme import Theme, ThemeRegistrationError, theme_manager

    class MockTheme(Theme):
        name: Literal["mock_theme"] = "mock_theme"

        async def render(self, _):
            return ""

    assert len(theme_manager) == 5
    assert "arknights" in theme_manager
    assert "basic" in theme_manager
    assert "brief" in theme_manager
    assert "ceobecanteen" in theme_manager
    assert "ht2i" in theme_manager
    assert "mock_theme" not in theme_manager

    theme_manager.register(MockTheme())
    assert len(theme_manager) == 6
    assert "mock_theme" in theme_manager

    # duplicated registration
    with pytest.raises(ThemeRegistrationError, match="duplicate"):
        theme_manager.register(MockTheme())

    theme_manager.unregister("mock_theme")
