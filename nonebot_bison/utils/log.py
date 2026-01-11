from collections.abc import Awaitable, Callable
import json
import ssl
from types import CoroutineType
from typing import Any

import httpx
from nonebot.log import logger

from nonebot_bison.setting import plugin_config


def catch_network_error[**P, R](func: Callable[P, Awaitable[R]]) -> Callable[P, CoroutineType[Any, Any, R | None]]:
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
        try:
            return await func(*args, **kwargs)
        except httpx.RequestError as err:
            if plugin_config.bison_show_network_warning:
                logger.warning(f"network connection error: {type(err)}, url: {err.request.url}")
            return None
        except ssl.SSLError as err:
            if plugin_config.bison_show_network_warning:
                logger.warning(f"ssl error: {err}")
            return None
        except json.JSONDecodeError as err:
            logger.warning(f"json error, parsing: {err.doc}")
            raise err

    return wrapper
