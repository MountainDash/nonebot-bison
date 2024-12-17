from time import time
from typing import Any, ClassVar

from nonebug.app import App
import pytest

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
def dummy_user(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    user = TargetQQGroup(group_id=123)
    return user


@pytest.fixture
def user_info_factory(app: App, dummy_user):
    from nonebot_bison.types import UserSubInfo

    def _user_info(category_getter, tag_getter):
        return UserSubInfo(dummy_user, category_getter, tag_getter)

    return _user_info


@pytest.fixture
def mock_platform_without_cats_tags(app: App):
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
                raw_post["text"],
                "http://t.tt/" + str(self.get_id(raw_post)),
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
def mock_platform(app: App):
    from nonebot_bison.platform.platform import NewMessage
    from nonebot_bison.post import Post
    from nonebot_bison.types import Category, RawPost, Tag, Target
    from nonebot_bison.utils import Site

    class MockSite(Site):
        name = "mock_site"
        schedule_type = "interval"
        schedule_setting: ClassVar[dict] = {"seconds": 100}

    class MockPlatform(NewMessage):
        platform_name = "mock_platform"
        name = "Mock Platform"
        enabled = True
        is_common = True
        enable_tag = True
        has_target = True
        site = MockSite
        categories: ClassVar[dict] = {
            Category(1): "转发",
            Category(2): "视频",
        }

        sub_index = 0

        @staticmethod
        async def get_target_name(_: "Target"):
            return "MockPlatform"

        def get_id(self, post: "RawPost") -> Any:
            return post["id"]

        def get_date(self, raw_post: "RawPost") -> float:
            return raw_post["date"]

        def get_tags(self, raw_post: "RawPost") -> list["Tag"]:
            return raw_post["tags"]

        def get_category(self, raw_post: "RawPost") -> "Category":
            return raw_post["category"]

        async def parse(self, raw_post: "RawPost") -> "Post":
            return Post(
                self,
                raw_post["text"],
                "http://t.tt/" + str(self.get_id(raw_post)),
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
def mock_site(app):
    from nonebot_bison.utils import Site

    class MockSite(Site):
        name = "mock_site"
        schedule_type = "interval"
        schedule_setting: ClassVar[dict] = {"seconds": 100}

    return MockSite


@pytest.fixture
def mock_platform_no_target(app: App, mock_site):
    from nonebot_bison.platform.platform import CategoryNotSupport, NewMessage
    from nonebot_bison.post import Post
    from nonebot_bison.types import Category, RawPost, Tag, Target

    class MockPlatform(NewMessage):
        platform_name = "mock_platform"
        name = "Mock Platform"
        enabled = True
        is_common = True
        site = mock_site
        enable_tag = True
        has_target = False
        categories: ClassVar[dict] = {Category(1): "转发", Category(2): "视频", Category(3): "不支持"}

        sub_index = 0

        @staticmethod
        async def get_target_name(_: "Target"):
            return "MockPlatform"

        def get_id(self, post: "RawPost") -> Any:
            return post["id"]

        def get_date(self, raw_post: "RawPost") -> float:
            return raw_post["date"]

        def get_tags(self, raw_post: "RawPost") -> list["Tag"]:
            return raw_post["tags"]

        def get_category(self, raw_post: "RawPost") -> "Category":
            if raw_post["category"] == 3:
                raise CategoryNotSupport(raw_post["category"])
            return raw_post["category"]

        async def parse(self, raw_post: "RawPost") -> "Post":
            return Post(
                self,
                raw_post["text"],
                "http://t.tt/" + str(self.get_id(raw_post)),
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
def mock_platform_no_target_2(app: App, mock_site):
    from nonebot_bison.platform.platform import NewMessage
    from nonebot_bison.post import Post
    from nonebot_bison.types import Category, RawPost, Tag, Target

    class MockPlatform(NewMessage):
        platform_name = "mock_platform"
        name = "Mock Platform"
        enabled = True
        site = mock_site
        is_common = True
        enable_tag = True
        has_target = False
        categories: ClassVar[dict] = {
            Category(4): "leixing4",
            Category(5): "leixing5",
        }

        sub_index = 0

        @classmethod
        async def get_target_name(cls, client, _: "Target"):
            return "MockPlatform"

        def get_id(self, post: "RawPost") -> Any:
            return post["id"]

        def get_date(self, raw_post: "RawPost") -> float:
            return raw_post["date"]

        def get_tags(self, raw_post: "RawPost") -> list["Tag"]:
            return raw_post["tags"]

        def get_category(self, raw_post: "RawPost") -> "Category":
            return raw_post["category"]

        async def parse(self, raw_post: "RawPost") -> "Post":
            return Post(
                self,
                raw_post["text"],
                "http://t.tt/" + str(self.get_id(raw_post)),
                nickname="Mock",
            )

        @classmethod
        async def get_sub_list(cls, _: "Target"):
            list_1 = [{"id": 5, "text": "p5", "date": now, "tags": ["tag1"], "category": 4}]

            list_2 = [
                *list_1,
                {"id": 6, "text": "p6", "date": now, "tags": ["tag1"], "category": 4},
                {"id": 7, "text": "p7", "date": now, "tags": ["tag2"], "category": 5},
            ]
            if cls.sub_index == 0:
                cls.sub_index += 1
                return list_1
            else:
                return list_2

    return MockPlatform


@pytest.fixture
def mock_status_change(app: App):
    from nonebot_bison.platform.platform import StatusChange
    from nonebot_bison.post import Post
    from nonebot_bison.types import Category, RawPost, Target

    class MockPlatform(StatusChange):
        platform_name = "mock_platform"
        name = "Mock Platform"
        enabled = True
        is_common = True
        enable_tag = False
        schedule_type = "interval"
        schedule_kw: ClassVar[dict] = {"seconds": 10}
        has_target = False
        categories: ClassVar[dict] = {
            Category(1): "转发",
            Category(2): "视频",
        }

        sub_index = 0

        @classmethod
        async def get_status(cls, _: "Target"):
            if cls.sub_index == 0:
                cls.sub_index += 1
                return {"s": False}
            elif cls.sub_index == 1:
                cls.sub_index += 1
                return {"s": True}
            else:
                return {"s": False}

        def compare_status(self, target, old_status, new_status) -> list["RawPost"]:
            if old_status["s"] is False and new_status["s"] is True:
                return [{"text": "on", "cat": 1}]
            elif old_status["s"] is True and new_status["s"] is False:
                return [{"text": "off", "cat": 2}]
            return []

        async def parse(self, raw_post) -> "Post":
            return Post(self, raw_post["text"], "")

        def get_category(self, raw_post):
            return raw_post["cat"]

    return MockPlatform


@pytest.mark.asyncio
async def test_new_message_target_without_cats_tags(mock_platform_without_cats_tags, user_info_factory):
    from nonebot_bison.types import SubUnit, Target
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    res1 = await mock_platform_without_cats_tags(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(Target("dummy"), [user_info_factory([1, 2], [])])
    )
    assert len(res1) == 0
    res2 = await mock_platform_without_cats_tags(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(Target("dummy"), [user_info_factory([], [])]),
    )
    assert len(res2) == 1
    posts_1 = res2[0][1]
    assert len(posts_1) == 3
    id_set_1 = {x.content for x in posts_1}
    assert "p2" in id_set_1
    assert "p3" in id_set_1
    assert "p4" in id_set_1


@pytest.mark.asyncio
async def test_new_message_target(mock_platform, user_info_factory):
    from nonebot_bison.types import SubUnit, Target
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    res1 = await mock_platform(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(Target("dummy"), [user_info_factory([1, 2], [])])
    )
    assert len(res1) == 0
    res2 = await mock_platform(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(
            Target("dummy"),
            [
                user_info_factory([1, 2], []),
                user_info_factory([1], []),
                user_info_factory([1, 2], ["tag1"]),
            ],
        ),
    )
    assert len(res2) == 3
    posts_1 = res2[0][1]
    posts_2 = res2[1][1]
    posts_3 = res2[2][1]
    assert len(posts_1) == 2
    assert len(posts_2) == 1
    assert len(posts_3) == 1
    id_set_1 = {x.content for x in posts_1}
    id_set_2 = {x.content for x in posts_2}
    id_set_3 = {x.content for x in posts_3}
    assert "p2" in id_set_1
    assert "p3" in id_set_1
    assert "p2" in id_set_2
    assert "p2" in id_set_3


@pytest.mark.asyncio
async def test_new_message_no_target(mock_platform_no_target, user_info_factory):
    from nonebot_bison.types import SubUnit, Target
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    res1 = await mock_platform_no_target(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(Target("dummy"), [user_info_factory([1, 2], [])])
    )
    assert len(res1) == 0
    res2 = await mock_platform_no_target(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(
            Target("dummy"),
            [
                user_info_factory([1, 2], []),
                user_info_factory([1], []),
                user_info_factory([1, 2], ["tag1"]),
            ],
        ),
    )
    assert len(res2) == 3
    posts_1 = res2[0][1]
    posts_2 = res2[1][1]
    posts_3 = res2[2][1]
    assert len(posts_1) == 2
    assert len(posts_2) == 1
    assert len(posts_3) == 1
    id_set_1 = {x.content for x in posts_1}
    id_set_2 = {x.content for x in posts_2}
    id_set_3 = {x.content for x in posts_3}
    assert "p2" in id_set_1
    assert "p3" in id_set_1
    assert "p2" in id_set_2
    assert "p2" in id_set_3
    res3 = await mock_platform_no_target(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(Target("dummy"), [user_info_factory([1, 2], [])])
    )
    assert len(res3) == 0


@pytest.mark.asyncio
async def test_status_change(mock_status_change, user_info_factory):
    from nonebot_bison.types import SubUnit, Target
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    res1 = await mock_status_change(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(Target("dummy"), [user_info_factory([1, 2], [])])
    )
    assert len(res1) == 0
    res2 = await mock_status_change(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(Target("dummy"), [user_info_factory([1, 2], [])])
    )
    assert len(res2) == 1
    posts = res2[0][1]
    assert len(posts) == 1
    assert posts[0].content == "on"
    res3 = await mock_status_change(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(
            Target("dummy"),
            [
                user_info_factory([1, 2], []),
                user_info_factory([1], []),
            ],
        ),
    )
    assert len(res3) == 2
    assert len(res3[0][1]) == 1
    assert res3[0][1][0].content == "off"
    assert len(res3[1][1]) == 0
    res4 = await mock_status_change(ProcessContext(DefaultClientManager())).fetch_new_post(
        SubUnit(Target("dummy"), [user_info_factory([1, 2], [])])
    )
    assert len(res4) == 0


@pytest.mark.asyncio
async def test_group(
    app: App,
    mock_platform_no_target,
    mock_platform_no_target_2,
    user_info_factory,
):
    from nonebot_bison.platform.platform import make_no_target_group
    from nonebot_bison.types import SubUnit, Target
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    dummy = Target("dummy")

    group_platform_class = make_no_target_group([mock_platform_no_target, mock_platform_no_target_2])
    group_platform = group_platform_class(ProcessContext(DefaultClientManager()))
    res1 = await group_platform.fetch_new_post(SubUnit(dummy, [user_info_factory([1, 4], [])]))
    assert len(res1) == 0
    res2 = await group_platform.fetch_new_post(SubUnit(dummy, [user_info_factory([1, 4], [])]))
    assert len(res2) == 1
    posts = res2[0][1]
    assert len(posts) == 2
    id_set_2 = {x.content for x in posts}
    assert "p2" in id_set_2
    assert "p6" in id_set_2
    res3 = await group_platform.fetch_new_post(SubUnit(dummy, [user_info_factory([1, 4], [])]))
    assert len(res3) == 0


async def test_batch_fetch_new_message(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.platform.platform import NewMessage
    from nonebot_bison.post import Post
    from nonebot_bison.types import RawPost, SubUnit, Target, UserSubInfo
    from nonebot_bison.utils import DefaultClientManager
    from nonebot_bison.utils.context import ProcessContext

    class BatchNewMessage(NewMessage):
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
                raw_post["text"],
                "http://t.tt/" + str(self.get_id(raw_post)),
                nickname="Mock",
            )

        @classmethod
        async def batch_get_sub_list(cls, targets: list[Target]) -> list[list[RawPost]]:
            assert len(targets) > 1
            if cls.sub_index == 0:
                cls.sub_index += 1
                res = [
                    [raw_post_list_2[0]],
                    [raw_post_list_2[1]],
                ]
            else:
                res = [
                    [raw_post_list_2[0], raw_post_list_2[2]],
                    [raw_post_list_2[1], raw_post_list_2[3]],
                ]
            res += [[]] * (len(targets) - 2)
            return res

    user1 = UserSubInfo(TargetQQGroup(group_id=123), [1, 2, 3], [])
    user2 = UserSubInfo(TargetQQGroup(group_id=234), [1, 2, 3], [])

    platform_obj = BatchNewMessage(ProcessContext(DefaultClientManager()))  # type:ignore

    res1 = await platform_obj.batch_fetch_new_post(
        [
            SubUnit(Target("target1"), [user1]),
            SubUnit(Target("target2"), [user1, user2]),
            SubUnit(Target("target3"), [user2]),
        ]
    )
    assert len(res1) == 0

    res2 = await platform_obj.batch_fetch_new_post(
        [
            SubUnit(Target("target1"), [user1]),
            SubUnit(Target("target2"), [user1, user2]),
            SubUnit(Target("target3"), [user2]),
        ]
    )
    assert len(res2) == 3
    send_set = set()
    for platform_target, posts in res2:
        for post in posts:
            send_set.add((platform_target, post.content))
    assert (TargetQQGroup(group_id=123), "p3") in send_set
    assert (TargetQQGroup(group_id=123), "p4") in send_set
    assert (TargetQQGroup(group_id=234), "p4") in send_set


async def test_batch_fetch_compare_status(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.platform.platform import StatusChange
    from nonebot_bison.post import Post
    from nonebot_bison.types import Category, RawPost, SubUnit, Target, UserSubInfo
    from nonebot_bison.utils import DefaultClientManager
    from nonebot_bison.utils.context import ProcessContext

    class BatchStatusChange(StatusChange):
        platform_name = "mock_platform"
        name = "Mock Platform"
        enabled = True
        is_common = True
        enable_tag = False
        schedule_type = "interval"
        schedule_kw: ClassVar[dict] = {"seconds": 10}
        has_target = True
        categories: ClassVar[dict] = {
            Category(1): "转发",
            Category(2): "视频",
        }

        sub_index = 0

        @classmethod
        async def batch_get_status(cls, targets: "list[Target]"):
            assert len(targets) > 0
            res = [{"s": cls.sub_index == 1} for _ in targets]
            res[0]["s"] = not res[0]["s"]
            if cls.sub_index == 0:
                cls.sub_index += 1
            return res

        def compare_status(self, target, old_status, new_status) -> list["RawPost"]:
            if old_status["s"] is False and new_status["s"] is True:
                return [{"text": "on", "cat": 1}]
            elif old_status["s"] is True and new_status["s"] is False:
                return [{"text": "off", "cat": 2}]
            return []

        async def parse(self, raw_post) -> "Post":
            return Post(self, raw_post["text"], "")

        def get_category(self, raw_post):
            return raw_post["cat"]

    batch_status_change = BatchStatusChange(ProcessContext(DefaultClientManager()))

    user1 = UserSubInfo(TargetQQGroup(group_id=123), [1, 2, 3], [])
    user2 = UserSubInfo(TargetQQGroup(group_id=234), [1, 2, 3], [])

    res1 = await batch_status_change.batch_fetch_new_post(
        [
            SubUnit(Target("target1"), [user1]),
            SubUnit(Target("target2"), [user1, user2]),
        ]
    )
    assert len(res1) == 0

    res2 = await batch_status_change.batch_fetch_new_post(
        [
            SubUnit(Target("target1"), [user1]),
            SubUnit(Target("target2"), [user1, user2]),
        ]
    )

    send_set = set()
    for platform_target, posts in res2:
        for post in posts:
            send_set.add((platform_target, post.content))
    assert len(send_set) == 3
    assert (TargetQQGroup(group_id=123), "off") in send_set
    assert (TargetQQGroup(group_id=123), "on") in send_set
    assert (TargetQQGroup(group_id=234), "on") in send_set
