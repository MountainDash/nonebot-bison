import functools

import httpx

from ..plugin_config import plugin_config

if plugin_config.bison_proxy:
    http_client = functools.partial(
        httpx.AsyncClient, proxies=plugin_config.bison_proxy
    )
else:
    http_client = httpx.AsyncClient
