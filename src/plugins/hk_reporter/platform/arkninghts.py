import httpx
import json
import time
from collections import defaultdict
from bs4 import BeautifulSoup as bs
from datetime import datetime
from nonebot import logger

from ..utils import Singleton, Render
from ..post import Post

@Singleton
class Arknights:
    
    def __init__(self):
        self.exists_posts = defaultdict(set)
        self.inited = defaultdict(lambda: False)

    async def get_announce_list(self):
        async with httpx.AsyncClient() as client:
            raw_data = client.get('http://ak-fs.hypergryph.com/announce/IOS/announcement.meta.json')
            return json.loads(raw_data.text)

    def filter(self, announce_data, inited=False) -> list[Post]:
        announce_list = announce_data['announceList']
        res: list[Post] = []
        for announce in announce_list:
            if inited:
                self.exists_posts['default'].add(announce['announceId'])
                continue
            if announce['announceId'] in self.exists_posts['default']:
                continue
            res.append(await self.parse(announce['webUrl']))
        return res

    async def parse(self, announce_url: str) -> Post:
        async with httpx.AsyncClient() as client:
            raw_html = client.get(announce_url)
        soup = bs(raw_html, 'html.parser')
        if soup.find("div", class_="standerd-container"):
            # 图文
            render = Render()
            render.
