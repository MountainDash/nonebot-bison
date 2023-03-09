import re
import sys
from typing import Union

import nonebot
from bs4 import BeautifulSoup as bs
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.log import default_format, logger
from nonebot.plugin import require

from ..plugin_config import plugin_config
from .context import ProcessContext
from .http import http_client
from .scheduler_config import SchedulerConfig, scheduler

__all__ = [
    "http_client",
    "Singleton",
    "parse_text",
    "ProcessContext",
    "html_to_text",
    "SchedulerConfig",
    "scheduler",
]


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


async def parse_text(text: str) -> MessageSegment:
    "return raw text if don't use pic, otherwise return rendered opcode"
    if plugin_config.bison_use_pic:
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import text_to_pic as _text_to_pic

        return MessageSegment.image(await _text_to_pic(text))
    else:
        return MessageSegment.text(text)


if not plugin_config.bison_skip_browser_check:
    require("nonebot_plugin_htmlrender")


def html_to_text(html: str, query_dict: dict = {}) -> str:
    html = re.sub(r"<br\s*/?>", "<br>\n", html)
    html = html.replace("</p>", "</p>\n")
    soup = bs(html, "html.parser")
    if query_dict:
        node = soup.find(**query_dict)
    else:
        node = soup
    assert node is not None
    return node.text.strip()


class Filter:
    def __init__(self) -> None:
        self.level: Union[int, str] = "DEBUG"

    def __call__(self, record):
        module_name: str = record["name"]
        module = sys.modules.get(module_name)
        if module:
            module_name = getattr(module, "__module_name__", module_name)
        record["name"] = module_name.split(".")[0]
        levelno = (
            logger.level(self.level).no if isinstance(self.level, str) else self.level
        )
        nonebot_warning_level = logger.level("WARNING").no
        return (
            record["level"].no >= levelno
            if record["name"] != "nonebot"
            else record["level"].no >= nonebot_warning_level
        )


if plugin_config.bison_filter_log:
    logger.remove()
    default_filter = Filter()
    logger.add(
        sys.stdout,
        colorize=True,
        diagnose=False,
        filter=default_filter,
        format=default_format,
    )
    config = nonebot.get_driver().config
    logger.success("Muted info & success from nonebot")
    default_filter.level = (
        ("DEBUG" if config.debug else "INFO")
        if config.log_level is None
        else config.log_level
    )
