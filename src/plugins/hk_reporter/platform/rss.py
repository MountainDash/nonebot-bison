from typing import Any, Optional
from ..types import RawPost, Target
from ..utils import Singleton
from ..post import Post
from .platform import Platform
from collections import defaultdict
from bs4 import BeautifulSoup as bs
from nonebot import logger
import feedparser
import httpx
import time
import calendar

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
        return Post('rss', text, raw_post.link, pics)
