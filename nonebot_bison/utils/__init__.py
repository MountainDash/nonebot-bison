import re
import sys
import difflib
from collections.abc import Callable

import nonebot
from nonebot.plugin import require
from bs4 import BeautifulSoup as bs
from nonebot.log import logger, default_format
from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from .http import http_client
from .context import ProcessContext
from ..plugin_config import plugin_config
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
            cls._instances[cls] = super().__call__(*args, **kwargs)
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
        self.level: int | str = "DEBUG"

    def __call__(self, record):
        module_name: str = record["name"]
        module = sys.modules.get(module_name)
        if module:
            module_name = getattr(module, "__module_name__", module_name)
        record["name"] = module_name.split(".")[0]
        levelno = logger.level(self.level).no if isinstance(self.level, str) else self.level
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
    default_filter.level = ("DEBUG" if config.debug else "INFO") if config.log_level is None else config.log_level


def text_similarity(str1, str2) -> float:
    """利用最长公共子序列的算法判断两个字符串是否相似，并返回0到1.0的相似度
    目前以大于0.8认定两个字符串相似
    当其中有一个字符串长度为0的特殊情况，认为两字符串相似，返回1.0
    """
    if len(str1) == 0 or len(str2) == 0:
        return 1.0
    matcher = difflib.SequenceMatcher(None, str1, str2)
    t = sum(temp.size for temp in matcher.get_matching_blocks())
    return t / min(len(str1), len(str2))


def similar_text_process(str1: str, str2: str, custom_comparison: dict[float, Callable[[str, str], str]]):
    """利用最长公共子序列的算法判断两个字符串是否相似，并返回0到1.0的相似度
    目前以大于等于0.8认定两个字符串相似
    当其中有一个字符串长度为0的特殊情况，认为两字符串相似，返回1.0
    :param str1: 第一个字符串
    :param str2: 第二个字符串
    :param custom_comparison: 自定义比较函数字典，键为相似度的阈值（浮点数），值为lambda函数
    """
    similarity = text_similarity(str1, str2)

    similarity_thresholds = sorted(custom_comparison.keys(), reverse=True)

    for threshold in similarity_thresholds:
        if similarity >= threshold:
            return custom_comparison[threshold](str1, str2)

    raise ValueError("No similarity threshold was met.")
