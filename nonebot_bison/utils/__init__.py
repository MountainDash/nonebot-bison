import difflib
import re
import sys
from typing import Any, ClassVar

from bs4 import BeautifulSoup as bs
import nonebot
from nonebot.log import default_format, logger
from nonebot.plugin import require
from nonebot_plugin_saa import Image, MessageSegmentFactory, Text

from nonebot_bison.plugin_config import plugin_config

from .context import ProcessContext as ProcessContext
from .http import http_client as http_client
from .image import capture_html as capture_html
from .image import is_pics_mergable as is_pics_mergable
from .image import pic_merge as pic_merge
from .image import pic_url_to_image as pic_url_to_image
from .image import text_to_image as text_to_image
from .site import ClientManager as ClientManager
from .site import DefaultClientManager as DefaultClientManager
from .site import Site as Site
from .site import anonymous_site as anonymous_site


class Singleton(type):
    _instances: ClassVar[dict[Any, Any]] = {}

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


def text_similarity(str1: str, str2: str) -> float:
    """利用最长公共子序列的算法判断两个字符串是否相似，并返回0到1.0的相似度"""
    if len(str1) == 0 or len(str2) == 0:
        raise ValueError("The length of string can not be 0")
    matcher = difflib.SequenceMatcher(None, str1, str2)
    t = sum(temp.size for temp in matcher.get_matching_blocks())
    return t / min(len(str1), len(str2))


def decode_unicode_escapes(s: str):
    """解码 \\r, \\n, \\t, \\uXXXX 等转义序列"""

    def decode_match(match: re.Match[str]) -> str:
        return bytes(match.group(0), "utf-8").decode("unicode_escape")

    regex = re.compile(r"\\[rnt]|\\u[0-9a-fA-F]{4}")
    return regex.sub(decode_match, s)


def text_fletten(text: str, *, banned: str = "\n\r\t", replace: str = " ") -> str:
    """将文本中的格式化字符去除"""
    return "".join(c if c not in banned else replace for c in text)
