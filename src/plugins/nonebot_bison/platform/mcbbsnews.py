import re
import time
from typing import Literal, Optional

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from httpx import AsyncClient

from ..post import Post
from ..types import Category, RawPost, Target
from ..utils import scheduler
from .platform import CategoryNotSupport, NewMessage


def _format_text(rawtext: str, mode: int) -> str:
    """处理BeautifulSoup生成的string中奇怪的回车+连续空格
    mode 0:处理标题
    mode 1:处理版本资讯类推文
    mode 2:处理快讯类推文"""
    match mode:
        case 0:
            ftext = re.sub(r"\n\s*", " ", rawtext)
        case 1:
            ftext = re.sub(r"[\n\s*]", "", rawtext)
        case 2:
            ftext = re.sub(r"\r\n", "", rawtext)
    return ftext


def _stamp_date(rawdate: str) -> int:
    """将时间转化为时间戳yyyy-mm-dd->timestamp"""
    time_stamp = int(time.mktime(time.strptime(rawdate, "%Y-%m-%d")))
    return time_stamp


class McbbsNews(NewMessage):
    categories = {1: "Java版本资讯", 2: "基岩版本资讯", 3: "快讯", 4: "基岩快讯", 5: "周边消息"}
    enable_tag = False
    platform_name = "mcbbsnews"
    name = "MCBBS幻翼块讯"
    enabled = True
    is_common = False
    scheduler = scheduler("interval", {"hours": 1})
    has_target = False

    @classmethod
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        return cls.name

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

    @staticmethod
    def _format_text(rawtext: str, mode: int) -> str:
        """处理BeautifulSoup生成的string中奇怪的回车+连续空格
        mode 0:处理标题
        mode 1:处理版本资讯类推文
        mode 2:处理快讯类推文"""
        if mode == 0:
            ftext = re.sub(r"\n\s*", " ", rawtext)
        elif mode == 1:
            ftext = re.sub(r"[\n\s*]", "", rawtext)
        elif mode == 2:
            ftext = re.sub(r"\r\n", "", rawtext)
        else:
            raise NotImplementedError
        return ftext

    @staticmethod
    def _stamp_date(rawdate: str) -> int:
        """将时间转化为时间戳yyyy-mm-dd->timestamp"""
        time_stamp = int(time.mktime(time.strptime(rawdate, "%Y-%m-%d")))
        return time_stamp

    def _gen_post_list(self, raw_post_list) -> list[RawPost]:
        """解析生成推文列表"""
        post_list = []
        for raw_post in raw_post_list:
            post = {}
            post["url"] = raw_post.find("a", class_="s xst")["href"]
            post["title"] = self._format_text(
                raw_post.find("a", class_="s xst").string, 0
            )
            post["category"] = raw_post.select("th em a")[0].string
            post["author"] = raw_post.select("td:nth-of-type(2) cite a")[0].string
            post["id"] = raw_post["id"]
            rawdate = (
                raw_post.select("td:nth-of-type(2) em span span")[0]["title"]
                if raw_post.select("td:nth-of-type(2) em span span")
                else raw_post.select("td:nth-of-type(2) em span")[0].string
            )
            post["date"] = self._stamp_date(rawdate)
            post_list.append(post)
        return post_list

    def get_id(self, post: RawPost) -> str:
        return post["id"]

    def get_date(self, post: RawPost) -> int:
        # 获取datetime精度只到日期，故暂时舍弃
        # return post["date"]
        return None

    def get_category(self, post: RawPost) -> Category:
        if post["category"] == "Java版本资讯":
            return Category(1)
        elif post["category"] == "基岩版本资讯":
            return Category(2)
        else:
            raise CategoryNotSupport("McbbsNews订阅暂不支持 `{}".format(post["category"]))

    @staticmethod
    def _check_str_chinese(check_str: str) -> bool:
        """检测字符串是否含有中文（有一个就算）"""
        for ch in check_str:
            if "\u4e00" <= ch <= "\u9fff":
                return True
        return False

    def _news_parser(self, raw_text: str, news_type: Literal["Java版本资讯", "基岩版本资讯"]):
        """提取Java/Bedrock版本资讯的推送消息"""
        raw_soup = BeautifulSoup(raw_text.replace("<br />", ""), "html.parser")
        # 获取头图
        if news_type == "Java版本资讯":
            # 获取头图
            pic_tag = raw_soup.find(
                "img", file=re.compile(r"https://www.minecraft.net/\S*header.jpg")
            )
            pic_url: list[str] = (
                [pic_tag.get("src", pic_tag.get("file"))] if pic_tag else []
            )
            # 获取blockquote标签下的内容
            soup = raw_soup.find(
                "td", id=re.compile(r"postmessage_[0-9]*")
            ).blockquote.blockquote
        elif news_type == "基岩版本资讯":
            # 获取头图
            pic_tag_0 = raw_soup.find(
                "img", file=re.compile(r"https://www.minecraft.net/\S*header.jpg")
            )
            pic_tag_1 = raw_soup.find(
                "img",
                file=re.compile(r"https://feedback.minecraft.net/\S*beta\S*.jpg"),
            )
            pic_url: list[str] = [
                pic_tag_0.get("src", pic_tag_0.get("file")) if pic_tag_0 else None,
                pic_tag_1.get("src", pic_tag_1.get("file")) if pic_tag_1 else None,
            ]
            # 获取blockquote标签下的内容
            soup = (
                raw_soup.find("td", id=re.compile(r"postmessage_[0-9]*"))
                .select("blockquote:nth-of-type(2)")[0]
                .blockquote
            )
        else:
            raise CategoryNotSupport(f"该函数不支持处理{news_type}")

        # 通用步骤
        # 删除无用的div和span段内容
        for del_tag in soup.find_all(["div", "span"]):
            del_tag.extract()
        # 进一步删除无用尾部
        # orig_info=soup.select("blockquote > strong")
        # orig_info[0].extract()
        # 展开所有的a,u和strong标签,展开ul,font标签里的font标签
        for unwrap_tag in soup.find_all(["a", "strong", "u", "ul", "font"]):
            if unwrap_tag.name in ["a", "strong", "u"]:  # 展开所有的a,u和strong标签
                unwrap_tag.unwrap()
            elif unwrap_tag.name in ["ul", "font"]:  # 展开ul,font里的font标签
                for font_tag in unwrap_tag.find_all("font"):
                    font_tag.unwrap()

        # 获取所有的中文句子
        post_text = ""
        last_is_empty_line = True
        for element in soup.contents:
            if isinstance(element, Tag):
                if element.name == "font":
                    text = ""
                    for sub in element.contents:
                        if isinstance(sub, NavigableString):
                            text += sub
                    if self._check_str_chinese(text):
                        post_text += "{}\n".format(self._format_text(text, 1))
                        last_is_empty_line = False
                elif element.name == "ul":
                    for li_tag in element.find_all("li"):
                        text = ""
                        for sub in li_tag.contents:
                            if isinstance(sub, NavigableString):
                                text += sub
                        if self._check_str_chinese(text):
                            post_text += "{}\n".format(self._format_text(text, 1))
                            last_is_empty_line = False
                else:
                    continue
            elif isinstance(element, NavigableString):
                if str(element) == "\n":
                    if not last_is_empty_line:
                        post_text += "\n"
                    last_is_empty_line = True
                else:
                    post_text += "{}\n".format(self._format_text(element, 1))
                    last_is_empty_line = False
            else:
                continue
        return post_text, pic_url

    def _express_parser(self, raw_text: str, news_type: Literal["快讯", "基岩快讯", "周边消息"]):
        """提取快讯/基岩快讯/周边消息的推送消息"""
        raw_soup = BeautifulSoup(raw_text.replace("<br />", ""), "html.parser")
        # 获取原始推文内容
        soup = raw_soup.find("td", id=re.compile(r"postmessage_[0-9]*"))
        if tag := soup.find("ignore_js_op"):
            tag.extract()
        # 获取所有图片
        pic_urls = []
        for img_tag in soup.find_all("img"):
            pic_url = img_tag.get("file") or img_tag.get("src")
            pic_urls.append(pic_url)
        # 验证是否有blockquote标签
        has_bolockquote = soup.find("blockquote")
        # 删除无用的span,div段内容
        for del_tag in soup.find_all("i"):
            del_tag.extract()
        if extag := soup.find(class_="attach_nopermission attach_tips"):
            extag.extract()
        # 展开所有的a,strong标签
        for unwrap_tag in soup.find_all(["a", "strong"]):
            unwrap_tag.unwrap()
        # 展开blockquote标签里的blockquote标签
        for b_tag in soup.find_all("blockquote"):
            for unwrap_tag in b_tag.find_all("blockquote"):
                unwrap_tag.unwrap()
        # 获取推文
        text = ""
        if has_bolockquote:
            for post in soup.find_all("blockquote"):
                # post.font.unwrap()
                for string in post.stripped_strings:
                    text += "{}\n".format(string)
        else:
            for string in soup.stripped_strings:
                text += "{}\n".format(string)
        ftext = self._format_text(text, 2)
        return ftext, pic_urls

    async def parse(self, raw_post: RawPost) -> Post:
        """获取并分配正式推文交由相应的函数解析"""
        post_url = "https://www.mcbbs.net/{}".format(raw_post["url"])
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/51.0.2704.63 Safari/537.36"
        }

        async with httpx.AsyncClient() as client:
            html = await client.get(post_url, headers=headers)

        if raw_post["category"] in ["Java版本资讯", "基岩版本资讯"]:
            # 事先删除不需要的尾部
            raw_text = re.sub(r"【本文排版借助了：[\s\S]*】", "", html.text)
            text, pic_urls = self._news_parser(raw_text, raw_post["category"])
        elif raw_post["category"] in ["快讯", "基岩快讯", "周边消息"]:
            text, pic_urls = self._express_parser(html.text, raw_post["category"])
        else:
            raise CategoryNotSupport("McbbsNews订阅暂不支持 `{}".format(raw_post["category"]))

        return Post(
            self.name,
            text="{}\n\n{}".format(raw_post["title"], text),
            url=post_url,
            pics=pic_urls,
            target_name=raw_post["category"],
        )
