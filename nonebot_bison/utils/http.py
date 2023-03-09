import functools

import httpx

from ..plugin_config import plugin_config

http_args = {
    "proxies": plugin_config.bison_proxy or None,
}
http_headers = {"user-agent": plugin_config.bison_ua}


@functools.wraps(httpx.AsyncClient)
def http_client(*args, **kwargs):
    if headers := kwargs.get("headers"):
        new_headers = http_headers.copy()
        new_headers.update(headers)
        kwargs["headers"] = new_headers
    else:
        kwargs["headers"] = http_headers
    return httpx.AsyncClient(*args, **kwargs)


http_client = functools.partial(http_client, **http_args)
