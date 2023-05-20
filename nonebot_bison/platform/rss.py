import calendar
from typing import Any, Optional

import feedparser
from bs4 import BeautifulSoup as bs
from httpx import AsyncClient

from ..post import Post
from ..types import RawPost, Target
from ..utils import SchedulerConfig, jaccard_text_similarity
from .platform import NewMessage


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
        title = raw_post.get("title", "")
        soup = bs(raw_post.description, "html.parser")
        desc = soup.text.strip()
        if not title or not desc:
            text = title or desc
        else:
            if len(desc) > len(title):
                desc2 = desc[: len(title)]
                title2 = title
                desc3 = desc[-len(title) :]
                title3 = title
            else:
                desc2 = desc
                title2 = title[: len(desc)]
                desc3 = desc
                title3 = title[-len(desc) :]

            if (
                jaccard_text_similarity(desc2, title2) > 0.8
                or jaccard_text_similarity(desc3, title3) > 0.8
            ):
                text = desc if len(desc) > len(title) else title
            else:
                text = f"{title}\n\n{desc}"

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
