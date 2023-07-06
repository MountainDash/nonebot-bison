import re
import sys
from typing import Union

import nonebot
from bs4 import BeautifulSoup as bs
from nonebot.log import default_format, logger
from nonebot.plugin import require
from nonebot_plugin_saa import Image, MessageSegmentFactory, Text

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


async def parse_text(text: str) -> MessageSegmentFactory:
    "return raw text if don't use pic, otherwise return rendered opcode"
    if plugin_config.bison_use_pic:
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import text_to_pic as _text_to_pic

        return Image(await _text_to_pic(text))
    else:
        return Text(text)


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


def jaccard_text_similarity(str1: str, str2: str) -> float:
    """
    计算两个字符串(基于字符)的
    [Jaccard相似系数](https://zh.wikipedia.org/wiki/雅卡尔指数)
    是否达到阈值
    """
    set1 = set(str1)
    set2 = set(str2)
    return len(set1 & set2) / len(set1 | set2)


def longest_common_subsequence_similarity(str1, str2):
    m = len(str1)
    n = len(str2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if str1[i - 1] == str2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    return dp[m][n] / min(m, n)
