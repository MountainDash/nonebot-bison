from ..utils import Singleton
from ..post import Post
from collections import defaultdict
from bs4 import BeautifulSoup as bs
from nonebot import logger
import feedparser
import httpx
import time
import calendar

async def get_rss_raw_data(url) -> str:
    async with httpx.AsyncClient() as client:
        res = await client.get(url, timeout=10.0)
        return res.text

async def get_rss_info(url) -> str:
    data = await get_rss_raw_data(url)
    feed = feedparser.parse(data)
    return feed.feed.title

class Rss(metaclass=Singleton):

    def __init__(self):
        self.exists_posts = defaultdict(set)
        self.inited = defaultdict(lambda: False)

    def filter(self, data, target, init=False) -> list[Post]:
        feed = feedparser.parse(data)
        entries = feed.entries
        res = []
        for entry in entries:
            entry_id = entry.id
            if init:
                self.exists_posts[target].add(entry_id)
                continue
            if entry_id in self.exists_posts[target]:
                continue
            # if time.time() - calendar.timegm(entry.published_parsed) > 2 * 60 * 60:
            #     continue
            res.append(self.parse(entry, target))
        return res

    def parse(self, entry, target) -> Post:
        soup = bs(entry.description, 'html.parser')
        text = soup.text
        pics = list(map(lambda x: x.attrs['src'], soup('img')))
        self.exists_posts[target].add(entry.id)
        return Post('rss', text, entry.link, pics)

    async def fetch_new_post(self, target) -> list[Post]:
        try:
            raw_data = await get_rss_raw_data(target)
            if self.inited[target]:
                return self.filter(raw_data, target)
            else:
                self.filter(raw_data, target, True)
                logger.info('rss init {} success'.format(target))
                logger.info('post list: {}'.format(self.exists_posts[target]))
                self.inited[target] = True
                return []
        except httpx.RequestError as err:
            logger.warning("network connection error: {}, url: {}".format(type(err), err.request.url))
            return []
