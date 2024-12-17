from nonebug.app import App
import pytest

from .utils import get_json


@pytest.fixture(scope="module")
def test_cases():
    return get_json("tag_cases.json")


# 测试正反tag的判断情况
@pytest.mark.asyncio
async def test_filter_user_custom_tag(app: App, test_cases):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    bilibili = platform_manager["bilibili"](ProcessContext(DefaultClientManager()))
    for case in test_cases:
        res = bilibili.is_banned_post(**case["case"])
        assert res == case["result"]


# 测试正反tag的分离情况
@pytest.mark.asyncio
async def test_tag_separator(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import DefaultClientManager, ProcessContext

    bilibili = platform_manager["bilibili"](ProcessContext(DefaultClientManager()))
    tags = ["~111", "222", "333", "~444", "555"]
    res = bilibili.tag_separator(tags)
    assert res[0] == ["222", "333", "555"]
    assert res[1] == ["111", "444"]
