from copy import deepcopy
from inspect import cleandoc
from time import time
from typing import TYPE_CHECKING, Any, ClassVar

from flaky import flaky
from nonebug import App
import pytest
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from nonebot_bison.post import Post

now = time()
passed = now - 3 * 60 * 60
raw_post_list_1 = [{"id": 1, "text": "p1", "date": now, "tags": ["tag1"], "category": 1}]

raw_post_list_2 = [
    *raw_post_list_1,
    {"id": 2, "text": "p2", "date": now, "tags": ["tag1"], "category": 1},
    {"id": 3, "text": "p3", "date": now, "tags": ["tag2"], "category": 2},
    {"id": 4, "text": "p4", "date": now, "tags": ["tag2"], "category": 3},
]


@pytest.fixture
def MERGEABLE_PNG_DATA() -> bytes:
    from tests.platforms.utils import get_bytes

    return get_bytes("mergeable-pic.jpg")


@pytest.fixture
def SIMPLE_PNG_DATA() -> bytes:
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"


@pytest.fixture
def mock_platform(app: App):
    from nonebot_bison.platform.platform import NewMessage
    from nonebot_bison.post import Post
    from nonebot_bison.types import RawPost, Target

    class MockPlatform(NewMessage):
        platform_name = "mock_platform"
        name = "Mock Platform"
        enabled = True
        is_common = True
        schedule_interval = 10
        enable_tag = False
        categories: ClassVar[dict] = {}
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
                content=raw_post["text"],
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


@pytest.fixture
def mock_post(app: App, mock_platform):
    from nonebot_bison.post import Post
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    return Post(
        m := mock_platform(ProcessContext(DefaultClientManager())),
        content="text",
        title="title",
        images=["http://t.tt/1.jpg"],
        timestamp=1234567890,
        url="http://t.tt/1",
        avatar="http://t.tt/avatar.jpg",
        nickname="Mock",
        description="description",
        repost=Post(
            m,
            content="repost",
            title="repost-title",
            images=["http://t.tt/2.jpg"],
            timestamp=1234567891,
            url="http://t.tt/2",
            avatar="http://t.tt/avatar-re.jpg",
            nickname="re-Mock",
            description="re-description",
        ),
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
async def test_theme_no_enable_use_browser(app: App, mock_post, mocker: MockerFixture):
    from nonebot_bison.plugin_config import plugin_config

    mocker.patch.object(plugin_config, "bison_use_browser", False)

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


@pytest.mark.asyncio
@flaky(max_runs=3, min_passes=1)
async def test_arknights_theme(app: App, mock_post):
    from nonebot_plugin_saa import Image, Text

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
async def test_basic_theme(app: App, mock_post: "Post", MERGEABLE_PNG_DATA, SIMPLE_PNG_DATA):
    from nonebot_plugin_saa import Image, Text

    from nonebot_bison.theme import theme_manager
    from nonebot_bison.theme.themes.basic import BasicTheme

    basic_theme = theme_manager["basic"]

    assert isinstance(basic_theme, BasicTheme)
    assert basic_theme.name == "basic"
    res = await basic_theme.render(mock_post)
    assert len(res) == 3
    assert res[0] == Text(
        cleandoc(
            """title

            text
            --------------
            转发自 re-Mock:
            repost-title

            repost
            --------------
            来源: Mock Platform Mock
            转发详情：http://t.tt/2
            详情: http://t.tt/1"""
        )
    )
    assert isinstance(res[1], Image)

    mock_post2 = deepcopy(mock_post)
    mock_post2.repost = None
    mock_post2.images = []
    res2 = await basic_theme.render(mock_post2)
    assert len(res2) == 1
    assert res2[0] == Text(
        cleandoc(
            """title

            text
            --------------
            来源: Mock Platform Mock
            详情: http://t.tt/1"""
        )
    )

    mock_post3 = deepcopy(mock_post)
    mock_post3.images = [MERGEABLE_PNG_DATA, MERGEABLE_PNG_DATA, MERGEABLE_PNG_DATA, SIMPLE_PNG_DATA]
    assert mock_post3.repost
    mock_post3.repost.images = [SIMPLE_PNG_DATA, SIMPLE_PNG_DATA]
    res3 = await basic_theme.render(mock_post3)
    assert len(res3) == 5


@pytest.mark.asyncio
async def test_brief_theme(app: App, mock_post):
    from nonebot_plugin_saa import Image, Text

    from nonebot_bison.theme import theme_manager
    from nonebot_bison.theme.themes.brief import BriefTheme

    brief_theme = theme_manager["brief"]

    assert isinstance(brief_theme, BriefTheme)
    assert brief_theme.name == "brief"
    res = await brief_theme.render(mock_post)
    assert len(res) == 2
    assert res[0] == Text(
        cleandoc(
            """title

            来源: Mock Platform Mock 的转发
            转发详情: http://t.tt/2
            详情: http://t.tt/1
            """
        )
    )
    assert isinstance(res[1], Image)

    mock_post2 = mock_post
    mock_post2.repost = None
    mock_post2.images = []
    res2 = await brief_theme.render(mock_post2)
    assert len(res2) == 1
    assert res2[0] == Text(
        cleandoc(
            """title

            来源: Mock Platform Mock
            详情: http://t.tt/1"""
        )
    )


@pytest.mark.render
@pytest.mark.asyncio
@flaky(max_runs=3, min_passes=1)
async def test_ceobecanteen_theme(app: App, mock_post: "Post", MERGEABLE_PNG_DATA, SIMPLE_PNG_DATA):
    from nonebot_plugin_saa import Image, Text

    from nonebot_bison.theme import theme_manager
    from nonebot_bison.theme.themes.ceobe_canteen import CeobeCanteenTheme

    ceobecanteen_theme = theme_manager["ceobecanteen"]

    assert isinstance(ceobecanteen_theme, CeobeCanteenTheme)
    assert ceobecanteen_theme.name == "ceobecanteen"
    res = await ceobecanteen_theme.render(mock_post)
    assert len(res) == 4
    assert isinstance(res[0], Image)
    assert isinstance(res[2], Image)
    assert res[1] == Text("来源: Mock Platform Mock\n详情: http://t.tt/1")

    mock_post2 = deepcopy(mock_post)
    assert mock_post2.repost
    mock_post2.repost.images = [MERGEABLE_PNG_DATA, MERGEABLE_PNG_DATA, MERGEABLE_PNG_DATA, SIMPLE_PNG_DATA]
    res2 = await ceobecanteen_theme.render(mock_post2)
    assert len(res2) == 5


@pytest.mark.render
@pytest.mark.asyncio
@flaky(max_runs=3, min_passes=1)
async def test_ht2i_theme(app: App, mock_post: "Post", MERGEABLE_PNG_DATA, SIMPLE_PNG_DATA):
    from nonebot_plugin_saa import Image, Text

    from nonebot_bison.theme import theme_manager
    from nonebot_bison.theme.themes.ht2i import Ht2iTheme

    ht2i_theme = theme_manager["ht2i"]

    assert isinstance(ht2i_theme, Ht2iTheme)
    assert ht2i_theme.name == "ht2i"
    res = await ht2i_theme.render(mock_post)
    assert len(res) == 4
    assert isinstance(res[0], Image)
    assert isinstance(res[2], Image)
    assert res[1] == Text("转发详情: http://t.tt/2\n详情: http://t.tt/1")

    mock_post2 = deepcopy(mock_post)
    mock_post2.repost = None
    mock_post2.images = [MERGEABLE_PNG_DATA, MERGEABLE_PNG_DATA, MERGEABLE_PNG_DATA, MERGEABLE_PNG_DATA]

    res2 = await ht2i_theme.render(mock_post2)

    assert len(res2) == 4
    assert res2[1] == Text("详情: http://t.tt/1")
