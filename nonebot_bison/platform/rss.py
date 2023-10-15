import time
import calendar
from typing import Any

import feedparser
from httpx import AsyncClient
from bs4 import BeautifulSoup as bs

from ..post import Post
from .platform import NewMessage
from ..types import Target, RawPost
from ..utils import SchedulerConfig, text_similarity


class RssSchedConf(SchedulerConfig):
    name = "rss"
    schedule_type = "interval"
    schedule_setting = {"seconds": 30}


class Rss(NewMessage):
    categories = {}
    enable_tag = False
    platform_name = "rss"
    name = "Rss"
    enabled = True
    is_common = True
    scheduler = RssSchedConf
    has_target = True

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        res = await client.get(target, timeout=10.0)
        feed = feedparser.parse(res.text)
        return feed["feed"]["title"]

    def get_date(self, post: RawPost) -> int:
        if hasattr(post, "published_parsed"):
            return calendar.timegm(post.published_parsed)
        elif hasattr(post, "updated_parsed"):
            return calendar.timegm(post.updated_parsed)
        else:
            return calendar.timegm(time.gmtime())

    def get_id(self, post: RawPost) -> Any:
        return post.id

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        res = await self.client.get(target, timeout=10.0)
        feed = feedparser.parse(res)
        entries = feed.entries
        for entry in entries:
            entry["_target_name"] = feed.feed.title
        return feed.entries

    def _text_process(self, title: str, desc: str) -> tuple[str | None, str]:
        """检查标题和描述是否相似，如果相似则标题为None, 否则返回标题和描述"""
        similarity = 1.0 if len(title) == 0 or len(desc) == 0 else text_similarity(title, desc)
        if similarity > 0.8:
            return None, title if len(title) > len(desc) else desc

        return title, desc

    async def parse(self, raw_post: RawPost) -> Post:
        title = raw_post.get("title", "")
        soup = bs(raw_post.description, "html.parser")
        desc = soup.text.strip()
        title, desc = self._text_process(title, desc)
        pics = [x.attrs["src"] for x in soup("img")]
        if raw_post.get("media_content"):
            for media in raw_post["media_content"]:
                if media.get("medium") == "image" and media.get("url"):
                    pics.append(media.get("url"))
        return Post(
            self,
            desc,
            title=title,
            url=raw_post.link,
            images=pics,
            nickname=raw_post["_target_name"],
        )
