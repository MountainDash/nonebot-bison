import re
import time

import httpx
from bs4 import BeautifulSoup

from ..types import Category, RawPost, Target
from .platform import CategoryNotSupport, NewMessage


def _format_text(rawtext: str) -> str:
    """处理BeautifulSoup生成的string中奇怪的回车+连续空格"""
    ftext = re.sub(r"\n\s*", " ", rawtext)
    return ftext


def _stamp_date(rawdate: str) -> int:
    """将时间转化为时间戳yyyy-mm-dd->timestamp"""
    time_stamp = int(time.mktime(time.strptime(rawdate, "%Y-%m-%d")))
    return time_stamp


class McbbsJavaNews(NewMessage):
    categories = {1: "Java版本资讯"}
    enable_tag = False
    platform_name = "mcbbsnews"
    name = "MCBBS幻翼块讯"
    enabled = True
    is_common = False
    schedule_type = "interval"
    schedule_kw = {"hours": 1}
    has_target = False

    async def get_target_name(self, _: Target) -> str:
        return f"{self.name} {self.categories[1]}"

    async def get_sub_list(self, _: Target) -> list[RawPost]:
        url = "https://www.mcbbs.net/forum-news-1.html"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/51.0.2704.63 Safari/537.36"
        }

        async with httpx.AsyncClient() as client:
            html = await client.get(url, headers=headers)
            soup = BeautifulSoup(html.text, "html.parser")
            raw_post_list = soup.find_all(
                "tbody", id=re.compile(r"normalthread_[0-9]*")
            )
            post_list = []
            for raw_post in raw_post_list:
                post = {}
                post["url"] = raw_post.find("a", class_="s xst")["href"]
                post["title"] = _format_text(raw_post.find("a", class_="s xst").string)
                post["category"] = raw_post.select("th em a")[0].string
                post["author"] = raw_post.select("td:nth-of-type(2) cite a")[0].string
                post["id"] = raw_post["id"]
                rawdate = (
                    raw_post.select("td:nth-of-type(2) em span span")[0]["title"]
                    if raw_post.select("td:nth-of-type(2) em span span")
                    else raw_post.select("td:nth-of-type(2) em span")[0].string
                )
                post["date"] = _stamp_date(rawdate)
                post_list.append(post)

        return post_list

    def get_id(self, post: RawPost) -> str:
        return post["id"]

    def get_date(self, post: RawPost) -> int:
        return post["date"]

    def get_category(self, post: RawPost) -> Category:
        if post["category"] == "Java版本资讯":
            return Category(1)
        else:
            return CategoryNotSupport("McbbsNews订阅暂不支持 `{}".format(post["category"]))
