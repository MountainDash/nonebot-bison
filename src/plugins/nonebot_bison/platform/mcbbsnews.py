import re
import time

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

from ..post import Post
from ..types import Category, RawPost, Target
from .platform import CategoryNotSupport, NewMessage


def _format_text(rawtext: str, mode: int) -> str:
    """处理BeautifulSoup生成的string中奇怪的回车+连续空格
    mode 0:处理标题
    mode 1:处理推文"""
    match mode:
        case 0:
            ftext = re.sub(r"\n\s*", " ", rawtext)
        case 1:
            ftext = re.sub(r"[\n\s*]", "", rawtext)
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
            post_list = self._gen_post_list(raw_post_list)

        return post_list

    def _gen_post_list(self, raw_post_list):
        post_list = []
        for raw_post in raw_post_list:
            post = {}
            post["url"] = raw_post.find("a", class_="s xst")["href"]
            post["title"] = _format_text(raw_post.find("a", class_="s xst").string, 0)
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
        match post["category"]:
            case "Java版本资讯":
                return Category(1)
            case _:
                raise CategoryNotSupport("McbbsNews订阅暂不支持 `{}".format(post["category"]))

    def _check_str_chinese(self, check_str: str) -> bool:
        """检测字符串是否含有中文（有一个就算）"""
        for ch in check_str:
            if "\u4e00" <= ch <= "\u9fff":
                return True
        return False

    def _javanews_parser(self, rawtext: str):
        """提取Java版本资讯的推送消息"""
        # 事先删除不需要的尾部
        rawtext = re.sub(r"【本文排版借助了：[\s\S]*】", "", rawtext)
        rawsoup = BeautifulSoup(rawtext.replace("<br />", ""), "html.parser")
        # 获取头图
        pic_tag = rawsoup.find(
            "img", file=re.compile(r"https://www.minecraft.net/\S*header.jpg")
        )
        pic_url: list[str] = [pic_tag.get("src", pic_tag.get("file"))]
        # 获取blockquote标签下的内容
        soup = rawsoup.find(
            "td", id=re.compile(r"postmessage_[0-9]*")
        ).blockquote.blockquote
        # 删除无用的div和span段内容
        for del_tag in soup.find_all(["div", "span"]):
            del_tag.extract()
        # 进一步删除无用尾部
        soup.select("blockquote > strong")[0].extract()
        # 展开所有的a,u和strong标签,展开ul,font标签里的font标签
        for unwrap_tag in soup.find_all(["a", "strong", "u", "ul", "font"]):
            match unwrap_tag.name:
                case "a" | "strong" | "u":  # 展开所有的a,u和strong标签
                    unwrap_tag.unwrap()
                case "ul" | "font":  # 展开ul,font里的font标签
                    for font_tag in unwrap_tag.find_all("font"):
                        font_tag.unwrap()

        # 获取所有的中文句子
        post_text = ""
        last_is_empty_line = True
        for element in soup.contents:
            if isinstance(element, Tag):
                match element.name:
                    case "font":
                        text = ""
                        for sub in element.contents:
                            if isinstance(sub, NavigableString):
                                text += sub
                        if self._check_str_chinese(text):
                            post_text += "\n{}".format(_format_text(text, 1))
                            last_is_empty_line = False
                    case "ul":
                        for li_tag in element.find_all("li"):
                            text = ""
                            for sub in li_tag.contents:
                                if isinstance(sub, NavigableString):
                                    text += sub
                            if self._check_str_chinese(text):
                                post_text += "\n{}".format(_format_text(text, 1))
                                last_is_empty_line = False
                    case _:
                        continue
            elif isinstance(element, NavigableString):
                if str(element) == "\n":
                    if not last_is_empty_line:
                        post_text += "\n"
                    last_is_empty_line = True
                else:
                    post_text += "\n{}".format(_format_text(element, 1))
                    last_is_empty_line = False
            else:
                continue
        return post_text, pic_url

    async def parse(self, raw_post: RawPost) -> Post:
        post_url = "https://www.mcbbs.net/{}".format(raw_post["url"])
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/51.0.2704.63 Safari/537.36"
        }
        async with httpx.AsyncClient() as client:
            html = await client.get(post_url, headers=headers)
            match raw_post["category"]:
                case "Java版本资讯":
                    text, pic_urls = self._javanews_parser(html)
                case _:
                    raise CategoryNotSupport(
                        "McbbsNews订阅暂不支持 `{}".format(raw_post["category"])
                    )
        return Post(
            self.name,
            text=text,
            url=post_url,
            pics=pic_urls,
            target_name=raw_post["category"],
        )
