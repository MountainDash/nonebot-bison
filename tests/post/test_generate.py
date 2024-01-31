from time import time
from typing import Any

import pytest
from nonebug.app import App
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


@pytest.mark.asyncio
async def test_generate_msg(mock_platform):
    from nonebot_plugin_saa import Text

    from nonebot_bison.post import Post
    from nonebot_bison.utils import ProcessContext

    post: Post = await mock_platform(ProcessContext(), AsyncClient()).parse(raw_post_list_1[0])
    assert post.platform.default_theme == "basic"
    res = await post.generate()
    assert len(res) == 1
    assert isinstance(res[0], Text)
    post.platform.default_theme = "ht2i"
    assert post.get_config_theme() is None
    assert set(post.get_priority_themes()) == {"basic", "ht2i"}
    assert post.get_priority_themes()[0] == "ht2i"
