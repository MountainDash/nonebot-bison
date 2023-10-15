from typing import Literal

import pytest
from nonebug import App


@pytest.mark.asyncio
async def test_registry_new_theme(app: App):
    from nonebot_bison.theme import AbstractTheme, ThemeRegistrationError, theme_manager

    class MockTheme(AbstractTheme):
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
    with pytest.raises(ThemeRegistrationError):
        theme_manager.register(MockTheme())
