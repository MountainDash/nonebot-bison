import pytest
from nonebug import App
from nonebug.fixture import nonebug_init


async def test_without_proxy(app: App):
    from nonebot_bison.utils import http_client

    c = http_client()
    assert not c._mounts


@pytest.mark.parametrize(
    "nonebug_init", [{"bison_proxy": "http://example.com"}], indirect=True
)
async def test_with_proxy(app: App):
    from nonebot_bison.utils import http_client

    c = http_client()
    assert c._mounts
