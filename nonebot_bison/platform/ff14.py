import re
from typing import Any, ClassVar

from bs4 import BeautifulSoup as bs
from httpx import AsyncClient
from nonebot.log import logger

from nonebot_bison.post import Post
from nonebot_bison.types import RawPost, Target
from nonebot_bison.utils import anonymous_site

from .platform import NewMessage

# 官网「最新情报」页（https://ff.web.sdo.com/web8/index.html#/newstab/newslist）
# 一次拉取的分类。8324~8327 是维护、更新一类的公告，之前的代码没带上，
# 这类公告一直抓不到
NEWS_CATEGORY_CODES = "8324,8325,8326,8327,5309,5310,5311,5312,5313"
# 文章被下架后 Summary 会被改成这个标记，官网列表页同样会把它们过滤掉
DELETED_SUMMARY = "333"

NEWS_LIST_URL = "https://cqnews.web.sdo.com/api/news/newsList"
NEWS_DETAIL_URL = "https://cqnews.web.sdo.com/api/news/newsDetail"
NEWS_ARTICLE_URL = "https://ff.web.sdo.com/web8/index.html#/newstab/newscont/{id}"


class FF14(NewMessage):
    categories: ClassVar[dict] = {}
    platform_name = "ff14"
    name = "最终幻想XIV官方公告"
    enable_tag = False
    enabled = True
    is_common = False
    scheduler_class = "ff14"
    site = anonymous_site("interval", {"seconds": 60})
    has_target = False

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "最终幻想XIV官方公告"

    async def get_sub_list(self, _) -> list[RawPost]:
        client = await self.ctx.get_client()
        raw_data = await client.get(
            NEWS_LIST_URL,
            params={
                "gameCode": "ff",
                "CategoryCode": NEWS_CATEGORY_CODES,
                "pageIndex": 0,
                "pageSize": 10,
            },
        )
        return [post for post in raw_data.json().get("Data") or [] if post.get("Summary") != DELETED_SUMMARY]

    def get_id(self, post: RawPost) -> Any:
        """用发布时间当作 ID

        因为有时候官方会直接编辑以前的文章内容
        """
        return post["PublishDate"]

    def get_date(self, _: RawPost) -> None:
        return None

    async def fetch_content(self, raw_post: RawPost) -> str:
        """公告正文

        列表接口的 Summary 只是标题长度的一句话（维护公告里干脆就是标题），
        完整正文要另请求详情接口。拿不到时退回 Summary，
        免得因为一次详情请求失败把整条公告丢掉
        """
        try:
            client = await self.ctx.get_client()
            raw_data = await client.get(NEWS_DETAIL_URL, params={"gameCode": "ff", "id": raw_post["Id"]})
            html: str = raw_data.json()["Data"]["Content"]
        except Exception as err:
            logger.warning(f"fetch ff14 news {raw_post['Id']} content failed: {err!r}")
            return raw_post["Summary"]

        text = bs(html, "html.parser").get_text("\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text.replace("\xa0", " "))
        return text or raw_post["Summary"]

    async def parse(self, raw_post: RawPost) -> Post:
        title = raw_post["Title"]
        uri = raw_post.get("OutLink") or NEWS_ARTICLE_URL.format(id=raw_post["Id"])
        return Post(
            self,
            content=await self.fetch_content(raw_post),
            title=title,
            url=uri,
            nickname="最终幻想XIV官方公告",
        )
