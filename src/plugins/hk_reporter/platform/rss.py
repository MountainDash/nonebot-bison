import calendar
from typing import Any, Optional

from bs4 import BeautifulSoup as bs
import feedparser
import httpx

from ..post import Post
from ..types import RawPost, Target
from .platform import Platform

class Rss(Platform):

    categories = {}
    enable_tag = False
    platform_name = 'rss'

    @staticmethod
    async def get_account_name(target: Target) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            res = await client.get(target, timeout=10.0)
            feed = feedparser.parse(res.text)
            return feed['feed']['title']

    def get_date(self, post: RawPost) -> int:
        return calendar.timegm(post.published_parsed)

    def get_id(self, post: RawPost) -> Any:
        return post.id

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        async with httpx.AsyncClient() as client:
            res = await client.get(target, timeout=10.0)
            feed = feedparser.parse(res)
            return feed.entries

    async def parse(self, raw_post: RawPost) -> Post:
        soup = bs(raw_post.description, 'html.parser')
        text = soup.text
        pics = list(map(lambda x: x.attrs['src'], soup('img')))
        return Post('rss', text=text, url=raw_post.link, pics=pics)
