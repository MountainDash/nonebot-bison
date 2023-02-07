import pytest
from httpx import AsyncClient
from nonebug import App


@pytest.fixture
def twitter(app: App):
    from nonebot_bison.platform import platform_manager
    from nonebot_bison.utils import ProcessContext

    return platform_manager["twitter"](ProcessContext(), AsyncClient())


@pytest.mark.asyncio
async def test_twitter_session_initial(twitter):
    await twitter._reset_session(force=True)
    assert twitter._header["x-csrf-token"] is not None
    assert twitter._header["x-guest-token"] is not None
    assert twitter._cookie is not None
    assert twitter._cookie["_twitter_sess"] is not None
