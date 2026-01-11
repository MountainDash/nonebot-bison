from nonebot_bison import core, utils
from nonebot_bison.core.platform import FetchMixin, FilterMixin, Platform, PlatformConfig
from nonebot_bison.core.site import SiteConfig


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
    )

    def parse(self, raw_post: str) -> core.post.Post:
        return core.post.Post(
            platform=self,
            content=raw_post,
        )

    async def fetch(self, sub_unit: core.platform.SubUnit) -> core.platform.TargetedPosts:
        # Simulate fetching posts
        posts = [self.parse(f"Test post {i} from {sub_unit.target}") for i in range(3)]
        return [(core.platform.PlatformTarget(self.platform_config.display_name, sub_unit.target), posts)]

