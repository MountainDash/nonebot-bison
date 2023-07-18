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

    async def parse(self, raw_post: RawPost) -> Post:
        title = raw_post.get("title", "")
        soup = bs(raw_post.description, "html.parser")
        desc = soup.text.strip()
        if not title or not desc:
            text = title or desc
        else:
            if text_similarity(desc, title) > 0.8:
                text = desc if len(desc) > len(title) else title
            else:
                text = f"{title}\n\n{desc}"

        pics = [x.attrs["src"] for x in soup("img")]
        if raw_post.get("media_content"):
            for media in raw_post["media_content"]:
                if media.get("medium") == "image" and media.get("url"):
                    pics.append(media.get("url"))
        return Post(
            "rss",
            text=text,
            url=raw_post.link,
            pics=pics,
            target_name=raw_post["_target_name"],
        )
