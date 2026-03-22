import anyio
from nonebot import logger, require

require("nonebot_plugin_saa")
require("nonebot_bison")
from nonebot_plugin_saa import TargetQQGroup

from nonebot_bison import core
from nonebot_bison.core.courier import Courier, Parcel, post_to_courier
from nonebot_bison.core.platform import FetchMixin, FilterMixin, Platform, PlatformConfig
from nonebot_bison.core.site import SiteConfig
from nonebot_bison.typing import SubUnit, SubUnits, Target, UserSubInfo
from nonebot_bison.utils.client_mgr import DefaultClientManager
from nonebot_bison.utils.store import MemoryStore


class TestPlatform(Platform, FetchMixin, FilterMixin):
    platform_config = PlatformConfig(
        name="TestPlatform",
        has_target=True,
        display_name="TestPlatform",
        preferred_theme="basic",
    )
    site_config = SiteConfig(
        name="TestSite",
        schedule_type="interval",
        schedule_setting={"seconds": 60},
        client_mgr=DefaultClientManager,
        require_browser=False,
        store_cls=MemoryStore,
    )

    def parse(self, raw_post: str) -> core.post.Post:
        return core.post.Post(
            platform=self.platform_config,
            content=raw_post,
        )

    async def fetch(self, sub_unit: core.platform.SubUnit) -> core.platform.TargetedPosts:
        # Simulate fetching posts
        posts = [self.parse(f"Test post {i} from {sub_unit.sub_target}") for i in range(3)]
        return [(TargetQQGroup(group_id=114514), posts)]


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
    cmgr = DefaultClientManager()
    store = MemoryStore()


    while True:
        if Courier._instance is None:
            logger.warning("courier not run")
            await anyio.sleep(2)
            continue
        await post_to_courier(
            create_schedule_parcel(
                SubUnit(Target("111"), [UserSubInfo(TargetQQGroup(group_id=114514), [], [])]),
                "TestPlatform",
                cmgr,
                store,
            )
        )
        logger.success("send a parcel")
        await anyio.sleep(5)


from nonebot import get_driver

d = get_driver()

@d.on_startup
async def a():
    d.task_group.start_soon(test_send_schedule_parcel, name="test")
