from typing import TypedDict, override

import anyio
from nonebot import logger, require

from nonebot_bison.core.post import Post
from nonebot_bison.core.theme import Theme, theme_manager

require("nonebot_plugin_saa")
require("nonebot_bison")
from nonebot_plugin_saa import TargetQQPrivate

from nonebot_bison import core
from nonebot_bison.core.courier import Courier, Parcel, post_to_courier
from nonebot_bison.core.platform import FetchMixin, FilterMixin, Platform, PlatformConfig
from nonebot_bison.core.site import SiteConfig
from nonebot_bison.typing import SubUnit, SubUnits, Target, UserSubInfo
from nonebot_bison.utils.client_mgr import DefaultClientManager
from nonebot_bison.utils.store import MemoryStore


class TestRawPost(TypedDict):
    content: str


class TestPlatform(Platform[TestRawPost], FetchMixin[TestRawPost], FilterMixin[TestRawPost]):
    platform_config = PlatformConfig(
        name="TestPlatform",
        has_target=True,
        display_name="TestPlatform",
        preferred_theme="test-theme",
    )
    site_config = SiteConfig(
        name="TestSite",
        schedule_type="interval",
        schedule_setting={"seconds": 60},
        client_mgr=DefaultClientManager,
        require_browser=False,
        store_cls=MemoryStore,
    )

    @override
    def parse(self, raw_post) -> core.post.Post:
        return core.post.Post(
            platform=self.platform_config,
            content=raw_post["content"],
        )

    @override
    async def fetch(self, sub_unit: core.platform.SubUnit):
        # Simulate fetching posts
        posts = [TestRawPost(content=f"Test post {i} from {sub_unit.sub_target}") for i in range(1)]
        return posts

    @override
    async def filter(self, target: Target, raw_posts):
        return tuple(raw_posts)

    @override
    def get_category(self, raw_post) -> None:
        return None

    @override
    def get_tags(self, raw_post) -> set[str]:
        return set()


class TestTheme(Theme[str]):
    name = "test-theme"

    @override
    def is_support_register(self) -> bool:
        return True

    @override
    async def is_support_render(self, post: Post) -> bool:
        return True

    @override
    async def render(self, post: Post):
        return post.content

theme_manager.register(TestTheme())
# ----


def create_schedule_parcel(
    sub_units: SubUnits,
    platform_name: str,
    cmgr,
    store,
) -> Parcel:
    return Parcel(
        tag="schedule",
        payload=sub_units,
        metadata={"platform_name": platform_name, "client_mgr": cmgr, "store": store},
    )


async def test_send_schedule_parcel():
    logger.success("hihi")
    cmgr = DefaultClientManager()
    store = MemoryStore()

    while True:
        if Courier._instance is None:
            logger.warning("courier not run")
            await anyio.sleep(2)
            continue
        await post_to_courier(
            create_schedule_parcel(
                SubUnit(Target("111"), [UserSubInfo(TargetQQPrivate(user_id=1836954163), [], [])]),
                "TestPlatform",
                cmgr,
                store,
            )
        )
        logger.success("send a parcel")
        await anyio.sleep(10)


from nonebot import get_driver

d = get_driver()


@d.on_startup
async def a():
    d.task_group.start_soon(test_send_schedule_parcel, name="test")
