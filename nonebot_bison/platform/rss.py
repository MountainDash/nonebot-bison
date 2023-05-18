import calendar
from typing import Any, Optional

import feedparser
from bs4 import BeautifulSoup as bs
from httpx import AsyncClient

from ..post import Post
from ..types import Category, RawPost, Target
from ..utils import SchedulerConfig
from .platform import NewMessage


class RssSchedConf(SchedulerConfig):
    name = "rss"
    schedule_type = "interval"
    schedule_setting = {"seconds": 30}


class Rss(NewMessage):
    categories = {1: "标题+正文"}
    enable_tag = False
    platform_name = "rss"
    name = "RSS"
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

    def get_category(self, _) -> Category:
        return Category(1)

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


class RssTitle(NewMessage):
    categories = {2: "仅标题"}
    enable_tag = False
    platform_name = "rss"
    name = "RSS"
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

    def get_category(self, _) -> Category:
        return Category(2)

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        res = await self.client.get(target, timeout=10.0)
        feed = feedparser.parse(res)
        entries = feed.entries
        for entry in entries:
            entry["_target_name"] = feed.feed.title
        return feed.entries

    async def parse(self, raw_post: RawPost) -> Post:
        text = raw_post.get("title", "") if raw_post.get("title") else ""
        # soup = bs(raw_post.description, "html.parser")
        # text += soup.text.strip()
        # pics = list(map(lambda x: x.attrs["src"], soup("img")))
        # if raw_post.get("media_content"):
        #     for media in raw_post["media_content"]:
        #         if media.get("medium") == "image" and media.get("url"):
        #             pics.append(media.get("url"))
        return Post(
            "rss",
            text=text,
            url=raw_post.link,
            pics=[],
            target_name=raw_post["_target_name"],
        )


class RssDesc(NewMessage):
    categories = {3: "仅正文"}
    enable_tag = False
    platform_name = "rss"
    name = "RSS"
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

    def get_category(self, _) -> Category:
        return Category(3)

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        res = await self.client.get(target, timeout=10.0)
        feed = feedparser.parse(res)
        entries = feed.entries
        for entry in entries:
            entry["_target_name"] = feed.feed.title
        return feed.entries

    async def parse(self, raw_post: RawPost) -> Post:
        # text = raw_post.get("title", "") + "\n" if raw_post.get("title") else ""
        soup = bs(raw_post.description, "html.parser")
        text = soup.text.strip()
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
