import typing
from pathlib import Path

import nonebot
import pytest
from nonebug.app import App


@pytest.fixture
async def app(nonebug_init: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import nonebot

    config = nonebot.get_driver().config
    config.bison_config_path = str(tmp_path)
    return App(monkeypatch)


@pytest.fixture
def dummy_user_subinfo(app: App):
    from nonebot_bison.types import User, UserSubInfo

    user = User("123", "group")
    return UserSubInfo(user=user, category_getter=lambda _: [], tag_getter=lambda _: [])
