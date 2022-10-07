import functools

import httpx

from ..plugin_config import plugin_config

http_args = {
    "proxies": plugin_config.bison_proxy or None,
    "headers": {"user-agent": plugin_config.bison_ua},
}

http_client = functools.partial(httpx.AsyncClient, **http_args)
