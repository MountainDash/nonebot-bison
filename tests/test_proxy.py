import importlib

from nonebug import App
from pytest_mock import MockerFixture


async def test_without_proxy(app: App):
    from nonebot_bison.utils import http_client

    c = http_client()
    assert not c._mounts
    req = c.build_request("GET", "http://example.com")
    assert "Chrome" in req.headers["User-Agent"]


async def test_with_proxy(app: App, mocker: MockerFixture):
    from nonebot_bison.plugin_config import plugin_config

    mocker.patch.object(plugin_config, "bison_proxy", "http://example.com")
    from nonebot_bison.utils import http

    importlib.reload(http)

    from nonebot_bison.utils.http import http_client

    c = http_client()
    assert c._mounts
