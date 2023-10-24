from time import time
from typing import Any

import pytest
from flaky import flaky
from nonebug import App
from httpx import AsyncClient

now = time()
passed = now - 3 * 60 * 60
raw_post_list_1 = [{"id": 1, "text": "p1", "date": now, "tags": ["tag1"], "category": 1}]

raw_post_list_2 = raw_post_list_1 + [
    {"id": 2, "text": "p2", "date": now, "tags": ["tag1"], "category": 1},
    {"id": 3, "text": "p3", "date": now, "tags": ["tag2"], "category": 2},
    {"id": 4, "text": "p4", "date": now, "tags": ["tag2"], "category": 3},
]


@pytest.fixture()
def mock_platform(app: App):
    from nonebot_bison.post import Post
    from nonebot_bison.types import Target, RawPost
    from nonebot_bison.platform.platform import NewMessage

    class MockPlatform(NewMessage):
        platform_name = "mock_platform"
        name = "Mock Platform"
        enabled = True
        is_common = True
        schedule_interval = 10
        enable_tag = False
        categories = {}
        has_target = True

        sub_index = 0

        @classmethod
        async def get_target_name(cls, client, _: "Target"):
            return "MockPlatform"

        def get_id(self, post: "RawPost") -> Any:
            return post["id"]

        def get_date(self, raw_post: "RawPost") -> float:
            return raw_post["date"]

        async def parse(self, raw_post: "RawPost") -> "Post":
            return Post(
                self,
                raw_post["text"],
                url="http://t.tt/" + str(self.get_id(raw_post)),
                nickname="Mock",
            )

        @classmethod
        async def get_sub_list(cls, _: "Target"):
            if cls.sub_index == 0:
                cls.sub_index += 1
                return raw_post_list_1
            else:
                return raw_post_list_2

    return MockPlatform


@pytest.fixture()
def mock_post(app: App, mock_platform):
    from nonebot_bison.post import Post
    from nonebot_bison.utils import ProcessContext

    return Post(
        mock_platform(ProcessContext(), AsyncClient()),
        "text",
        title="title",
        images=["http://t.tt/1.jpg"],
        timestamp=1234567890,
        url="http://t.tt/1",
        avatar="http://t.tt/avatar.jpg",
        nickname="Mock",
        description="description",
    )


@pytest.mark.asyncio
async def test_theme_need_browser(app: App, mock_post):
    from nonebot_bison.theme import Theme, theme_manager

    class MockTheme(Theme):
        name: str = "mock_theme"
        need_browser: bool = False

        async def render(self, post):
            return []

    theme = MockTheme()
    theme_manager.register(theme)
    mock_post.platform.default_theme = theme.name

    await theme.do_render(mock_post)
    assert not theme._browser_checked
    theme.need_browser = True
    await theme.do_render(mock_post)
    assert theme._browser_checked

    theme_manager.unregister(theme.name)


@pytest.mark.asyncio
async def test_theme_no_enable_use_browser(app: App, mock_post):
    from nonebot_bison.plugin_config import plugin_config

    plugin_config.bison_theme_use_browser = False

    from nonebot_bison.theme import Theme, ThemeRenderUnsupportError, theme_manager

    class MockTheme(Theme):
        name: str = "mock_theme"
        need_browser: bool = True

        async def render(self, post):
            return []

    theme = MockTheme()
    theme_manager.register(theme)
    mock_post.platform.default_theme = theme.name
    with pytest.raises(ThemeRenderUnsupportError, match="not support render"):
        await theme.do_render(mock_post)

    theme_manager.unregister(theme.name)
    plugin_config.bison_theme_use_browser = True


@pytest.mark.asyncio
@flaky(max_runs=3, min_passes=1)
async def test_arknights_theme(app: App, mock_post):
    from nonebot_plugin_saa import Text, Image

    from nonebot_bison.theme import theme_manager
    from nonebot_bison.theme.themes.arknights import ArknightsTheme

    arknights_theme = theme_manager["arknights"]

    assert isinstance(arknights_theme, ArknightsTheme)
    assert arknights_theme.name == "arknights"
    res = await arknights_theme.render(mock_post)
    assert len(res) == 2
    assert isinstance(res[0], Image)
    assert res[1] == Text("前往:http://t.tt/1")


@pytest.mark.asyncio
async def test_basic_theme(app: App, mock_post):
    from nonebot_plugin_saa import Text, Image

    from nonebot_bison.theme import theme_manager
    from nonebot_bison.theme.themes.basic import BasicTheme

    basic_theme = theme_manager["basic"]

    assert isinstance(basic_theme, BasicTheme)
    assert basic_theme.name == "basic"
    res = await basic_theme.render(mock_post)
    assert len(res) == 2
    assert res[0] == Text("title\n\ntext\n来源: Mock Platform Mock\n详情: http://t.tt/1")
    assert isinstance(res[1], Image)


@pytest.mark.asyncio
async def test_brief_theme(app: App, mock_post):
    from nonebot_plugin_saa import Text, Image

    from nonebot_bison.theme import theme_manager
    from nonebot_bison.theme.themes.brief import BriefTheme

    brief_theme = theme_manager["brief"]

    assert isinstance(brief_theme, BriefTheme)
    assert brief_theme.name == "brief"
    res = await brief_theme.render(mock_post)
    assert len(res) == 2
    assert res[0] == Text("title\n\n来源: Mock Platform Mock\n详情: http://t.tt/1")
    assert isinstance(res[1], Image)


@pytest.mark.render
@pytest.mark.asyncio
@flaky(max_runs=3, min_passes=1)
async def test_ceobecanteen_theme(app: App, mock_post):
    from nonebot_plugin_saa import Text, Image

    from nonebot_bison.theme import theme_manager
    from nonebot_bison.theme.themes.ceobe_canteen import CeobeCanteenTheme

    ceobecanteen_theme = theme_manager["ceobecanteen"]

    assert isinstance(ceobecanteen_theme, CeobeCanteenTheme)
    assert ceobecanteen_theme.name == "ceobecanteen"
    res = await ceobecanteen_theme.render(mock_post)
    assert len(res) == 3
    assert isinstance(res[0], Image)
    assert isinstance(res[2], Image)
    assert res[1] == Text("来源: Mock Platform Mock\n详情: http://t.tt/1")


@pytest.mark.render
@pytest.mark.asyncio
@flaky(max_runs=3, min_passes=1)
async def test_ht2i_theme(app: App, mock_post):
    from nonebot_plugin_saa import Text, Image

    from nonebot_bison.theme import theme_manager
    from nonebot_bison.theme.themes.ht2i import Ht2iTheme

    ht2i_theme = theme_manager["ht2i"]

    assert isinstance(ht2i_theme, Ht2iTheme)
    assert ht2i_theme.name == "ht2i"
    res = await ht2i_theme.render(mock_post)
    assert len(res) == 3
    assert isinstance(res[0], Image)
    assert isinstance(res[2], Image)
    assert res[1] == Text("详情: http://t.tt/1")
