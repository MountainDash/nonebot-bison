import pytest
from nonebug.app import App

from .utils import get_json


@pytest.fixture(scope="module")
def test_cases():
    return get_json("tag_cases.json")


@pytest.mark.asyncio
async def test_filter_user_custom_tag(app: App, test_cases):
    from nonebot_bison.platform import platform_manager

    bilibili = platform_manager["bilibili"]
    for case in test_cases:
        res = bilibili.is_banned_post(**case["case"])
        assert res == case["result"]
