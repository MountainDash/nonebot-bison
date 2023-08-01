import re
import time
import traceback

from httpx import AsyncClient
from nonebot.log import logger
from bs4 import Tag, BeautifulSoup
from nonebot.plugin import require

from ..post import Post
from ..types import Target, RawPost, Category
from ..utils import SchedulerConfig, http_client
from .platform import NewMessage, CategoryNotSupport, CategoryNotRecognize


class McbbsnewsSchedConf(SchedulerConfig):
    name = "mcbbsnews"
    schedule_type = "interval"
    schedule_setting = {"minutes": 30}


class McbbsNews(NewMessage):
    categories: dict[int, str] = {
        1: "Java版资讯",
        2: "基岩版资讯",
        3: "块讯",
        4: "基岩块讯",
        5: "周边",
        6: "主机",
        7: "时评",
    }
    enable_tag: bool = False
    platform_name: str = "mcbbsnews"
    name: str = "MCBBS幻翼块讯"
    enabled: bool = True
    is_common: bool = False
    scheduler = McbbsnewsSchedConf
    has_target: bool = False

    _known_cats: dict[int, str] = {
        1: "Java版资讯",
        2: "基岩版资讯",
        3: "块讯",
        4: "基岩块讯",
        5: "周边",
        6: "主机",
        7: "时评",
    }

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str:
        return cls.name

    async def get_sub_list(self, _: Target) -> list[RawPost]:
        url: str = "https://www.mcbbs.net/forum-news-1.html"

        html = await self.client.get(url)
        soup = BeautifulSoup(html.text, "html.parser")
        raw_post_list = soup.find_all("tbody", id=re.compile(r"normalthread_[0-9]*"))
        post_list = self._gen_post_list(raw_post_list)

        return post_list

    def _gen_post_list(self, raw_post_list: list[Tag]) -> list[RawPost]:
        """解析生成推文列表"""
        post_list = []

        for raw_post in raw_post_list:
            post = {}

            url_tag = raw_post.find("a", class_="s xst")
            if isinstance(url_tag, Tag):
                post["url"] = url_tag.get("href")
            title_tag = raw_post.find("a", class_="s xst")
            if isinstance(title_tag, Tag):
                title_string = title_tag.string
                if isinstance(title_string, str):
                    post["title"] = self._format_text(title_string, "title")
            post["category"] = raw_post.select("th em a")[0].string
            post["author"] = raw_post.select("td:nth-of-type(2) cite a")[0].string
            post["id"] = raw_post["id"]
            raw_date = (
                raw_post.select("td:nth-of-type(2) em span span")[0]["title"]
                if raw_post.select("td:nth-of-type(2) em span span")
                else raw_post.select("td:nth-of-type(2) em span")[0].string
            )
            if isinstance(raw_date, str):
                post["date"] = self._stamp_date(raw_date)

            post_list.append(post)

        return post_list

    @staticmethod
    def _format_text(raw_text: str, mode: str) -> str:
        """
            处理BeautifulSoup生成的string中奇怪的回车+连续空格

        参数:
            title: 处理标题
        """
        match mode:
            case "title":
                ftext = re.sub(r"\n\s*", " ", raw_text)
            case _:
                raise NotImplementedError("不支持的处理模式: {mode}")

        return ftext

    @staticmethod
    def _stamp_date(raw_date: str) -> int:
        """
        将时间转化为时间戳:
            yyyy-mm-dd -> timestamp
        """
        time_stamp = int(time.mktime(time.strptime(raw_date, "%Y-%m-%d")))

        return time_stamp

    def get_id(self, post: RawPost) -> str:
        return post["id"]

    def get_date(self, _: RawPost) -> int | None:
        # 获取datetime精度只到日期，故暂时舍弃
        # return post["date"]
        return None

    def get_category(self, post: RawPost) -> Category:
        categoty_name = post["category"]
        category_keys = list(self.categories.keys())
        category_values = list(self.categories.values())
        known_category_values = list(self._known_cats.values())

        if categoty_name in category_values:
            category_id = category_keys[category_values.index(categoty_name)]
        elif categoty_name in known_category_values:
            raise CategoryNotSupport(f"McbbsNews订阅暂不支持 {categoty_name}")
        else:
            raise CategoryNotRecognize(f"Mcbbsnews订阅尚未识别 {categoty_name}")
        return category_id

    async def parse(self, post: RawPost) -> Post:
        """获取并分配正式推文交由相应的函数渲染"""
        post_url = "https://www.mcbbs.net/{}".format(post["url"])
        async with http_client() as client:
            html = await client.get(post_url)
            html.raise_for_status()

        soup = BeautifulSoup(html.text, "html.parser")
        post_body = soup.find("td", id=re.compile(r"postmessage_[0-9]*"))
        if isinstance(post_body, Tag):
            post_id = post_body.attrs.get("id")
        else:
            post_id = None
        pics = await self._news_render(post_url, f"#{post_id}")

        return Post(
            self.name,
            text="{}\n│\n└由 {} 发表".format(post["title"], post["author"]),
            url=post_url,
            pics=list(pics),
            target_name=post["category"],
        )

    async def _news_render(self, url: str, selector: str) -> list[bytes]:
        """
        将给定的url网页的指定CSS选择器部分渲染成图片

        注意：
            一般而言每条新闻的长度都很可观，图片生成时间比较喜人
        """
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import text_to_pic, capture_element

        try:
            assert url
            pic_data = await capture_element(
                url,
                selector,
                viewport={"width": 1000, "height": 6400},
                device_scale_factor=3,
            )
            assert pic_data
        except Exception:
            err_info = traceback.format_exc()
            logger.warning(f"渲染错误：{err_info}")

            err_pic0 = await text_to_pic("错误发生！")
            err_pic1 = await text_to_pic(err_info)
            return [err_pic0, err_pic1]
        else:
            return [pic_data]
