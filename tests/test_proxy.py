import pytest
from nonebug import App


async def test_without_proxy(app: App):
    from nonebot_bison.utils import http_client

    c = http_client()
    assert not c._mounts
    req = c.build_request("GET", "http://example.com")
    assert "Chrome" in req.headers["User-Agent"]


@pytest.mark.parametrize(
    "nonebug_init", [{"bison_proxy": "http://example.com"}], indirect=True
)
async def test_with_proxy(app: App):
    from nonebot_bison.utils import http_client

    c = http_client()
    assert c._mounts
