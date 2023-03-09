import calendar
from typing import Any, Optional

import feedparser
from bs4 import BeautifulSoup as bs
from httpx import AsyncClient

from ..post import Post
from ..types import RawPost, Target
from ..utils import scheduler
from .platform import NewMessage


class Rss(NewMessage):

    categories = {}
    enable_tag = False
    platform_name = "rss"
    name = "Rss"
    enabled = True
    is_common = True
    scheduler = scheduler("interval", {"seconds": 30})
    has_target = True

    @classmethod
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        res = await client.get(target, timeout=10.0)
        feed = feedparser.parse(res.text)
        return feed["feed"]["title"]

    def get_date(self, post: RawPost) -> int:
        return calendar.timegm(post.published_parsed)

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
        text = raw_post.get("title", "") + "\n" if raw_post.get("title") else ""
        soup = bs(raw_post.description, "html.parser")
        text += soup.text.strip()
        pics = list(map(lambda x: x.attrs["src"], soup("img")))
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
