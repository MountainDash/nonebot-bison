from inspect import cleandoc
from time import time
from typing import Any, ClassVar

from nonebug.app import App
import pytest
from pytest_mock import MockerFixture

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
def mock_platform(app: App):
    from nonebot_bison.platform.platform import NewMessage
    from nonebot_bison.post import Post
    from nonebot_bison.types import RawPost, Target

    class MockPlatform(NewMessage):
        platform_name = "mock-platform"
        name = "Mock-Platform"
        enabled = True
        is_common = True
        schedule_interval = 10
        enable_tag = False
        categories: ClassVar[dict] = {}
        has_target = True

        sub_index = 0

        @classmethod
        async def get_target_name(cls, client, _: "Target"):
            return "MockPlatformTarget"

        def get_id(self, post: "RawPost") -> Any:
            return post["id"]

        def get_date(self, raw_post: "RawPost") -> float:
            return raw_post["date"]

        async def parse(self, raw_post: "RawPost") -> "Post":
            return Post(
                self,
                content=raw_post["text"],
                url="http://t.tt/" + str(self.get_id(raw_post)),
                nickname="MockNick",
            )

        @classmethod
        async def get_sub_list(cls, _: "Target"):
            if cls.sub_index == 0:
                cls.sub_index += 1
                return raw_post_list_1
            else:
                return raw_post_list_2

    return MockPlatform


async def test_display(mock_platform):
    from nonebot_bison.post import Post

    post1_content = cleandoc(
        "Rebum delenit iusto augue in rebum sanctus diam stet clita voluptua amet tempor sea in.\n"
        "Vel ullamcorper dolore clita eos amet tempor velit amet in.\n"
        "Vero hendrerit vero diam et lorem blandit ex diam ex amet.\n"
        "Voluptua et sed diam erat et diam lorem lorem no euismod sadipscing rebum feugiat est elitr autem.\n",
    )
    post1 = Post(
        mock_platform,
        content=post1_content,
        title="Ipsum consectetuer voluptua eirmod aliquyam dolore eu volutpat ipsum ipsum eirmod nulla.",
        images=[
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89",
        ],
        timestamp=1612345678,
        url="http://t.tt/diam-duo-autem-sed-sadipscing-invidunt",
        avatar=(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        ),
        nickname="Mock",
        description="Labore amet ut invidunt dolor consectetuer ipsum sadipscing sed minim diam rebum justo tincidunt.",
    )
    assert (
        str(post1)
        == rf"""## Post: {id(post1):X} ##

Rebum delenit iusto augue in rebum sanctus diam stet clita voluptua amet tempor sea in.
Vel ullamcorper dolore clita eos amet tempor velit amet in.
Vero hendrerit vero diam et lorem blandit ex diam ex...

来源: <Platform mock-platform>
附加信息:
- compress: False
- title: 'Ipsum consectetuer voluptua eirmod aliquyam dolore eu volutpat ipsum ipsum eirmod nulla.'
- images: [b'\x89PNG\r\n...f\x15\xc4\x89', b'\x89PNG\r\n...f\x15\xc4\x89']
- timestamp: 1612345678
- url: 'http://t.tt/diam-duo-autem-sed-sadipscing-invidunt'
- avatar: b'\x89PNG\r\n...f\x15\xc4\x89'
- nickname: 'Mock'
- description: 'Labore amet ut invidunt dolor consectetuer ipsum sadipscing sed minim diam rebum justo tincidunt.'
"""
    )

    post2_content = cleandoc(
        "Rebum delenit iusto augue in rebum sanctus diam stet clita voluptua amet tempor sea in.\n"
        "Vel ullamcorper dolore clita eos amet tempor velit amet in.\n"
        "Vero hendrerit vero diam et lorem blandit ex diam ex amet.\n"
        "Voluptua et sed diam erat et diam lorem lorem no euismod sadipscing rebum feugiat est elitr autem.\n",
    )
    post2 = Post(
        mock_platform,
        content=post2_content,
        title="Ipsum consectetuer voluptua eirmod aliquyam dolore eu volutpat ipsum ipsum eirmod nulla.",
        images=[
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89",
        ],
        timestamp=1612345678,
        url="http://t.tt/diam-duo-autem-sed-sadipscing-invidunt",
        avatar=(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        ),
        nickname="Mock2",
        description="Labore amet ut invidunt dolor consectetuer ipsum sadipscing sed minim diam rebum justo tincidunt.",
        repost=post1,
    )
    assert (
        str(post2)
        == rf"""## Post: {id(post2):X} ##

Rebum delenit iusto augue in rebum sanctus diam stet clita voluptua amet tempor sea in.
Vel ullamcorper dolore clita eos amet tempor velit amet in.
Vero hendrerit vero diam et lorem blandit ex diam ex...

来源: <Platform mock-platform>
附加信息:
- compress: False
- title: 'Ipsum consectetuer voluptua eirmod aliquyam dolore eu volutpat ipsum ipsum eirmod nulla.'
- images: [b'\x89PNG\r\n...f\x15\xc4\x89', b'\x89PNG\r\n...f\x15\xc4\x89']
- timestamp: 1612345678
- url: 'http://t.tt/diam-duo-autem-sed-sadipscing-invidunt'
- avatar: b'\x89PNG\r\n...f\x15\xc4\x89'
- nickname: 'Mock2'
- description: 'Labore amet ut invidunt dolor consectetuer ipsum sadipscing sed minim diam rebum justo tincidunt.'

转发:
## Post: {id(post1):X} ##

Rebum delenit iusto augue in rebum sanctus diam stet clita voluptua amet tempor sea in.
Vel ullamcorper dolore clita eos amet tempor velit amet in.
Vero hendrerit vero diam et lorem blandit ex diam ex...

来源: <Platform mock-platform>
附加信息:
- compress: False
- title: 'Ipsum consectetuer voluptua eirmod aliquyam dolore eu volutpat ipsum ipsum eirmod nulla.'
- images: [b'\x89PNG\r\n...f\x15\xc4\x89', b'\x89PNG\r\n...f\x15\xc4\x89']
- timestamp: 1612345678
- url: 'http://t.tt/diam-duo-autem-sed-sadipscing-invidunt'
- avatar: b'\x89PNG\r\n...f\x15\xc4\x89'
- nickname: 'Mock'
- description: 'Labore amet ut invidunt dolor consectetuer ipsum sadipscing sed minim diam rebum justo tincidunt.'
"""
    )


@pytest.mark.asyncio
async def test_generate_msg(mock_platform, mocker: MockerFixture):
    from nonebot_plugin_saa import Image, Text

    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.post import Post
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    post: Post = await mock_platform(ProcessContext(DefaultClientManager())).parse(raw_post_list_1[0])
    assert post.platform.default_theme == "basic"
    res = await post.generate()
    assert len(res) == 1
    assert isinstance(res[0], Text)
    assert str(res[0]) == "p1\n--------------\n来源: Mock-Platform MockNick\n详情: http://t.tt/1"

    post.platform.default_theme = "ht2i"
    assert post.get_config_theme() is None
    assert set(post.get_priority_themes()) == {"basic", "ht2i"}
    assert post.get_priority_themes()[0] == "ht2i"
    res1 = await post.generate()
    assert isinstance(res1[0], Image)

    mocker.patch.object(plugin_config, "bison_use_browser", False)

    res3 = await post.generate()
    assert res3[0]
    assert isinstance(res3[0], Text)


@pytest.mark.asyncio
@pytest.mark.render
async def test_msg_segments_convert(mock_platform, mocker: MockerFixture):
    from nonebot_plugin_saa import Image

    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.post import Post
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    mocker.patch.object(plugin_config, "bison_use_pic", True)

    post: Post = await mock_platform(ProcessContext(DefaultClientManager())).parse(raw_post_list_1[0])
    assert post.platform.default_theme == "basic"
    res = await post.generate_messages()
    assert len(res) == 1
    assert isinstance(res[0][0], Image)
