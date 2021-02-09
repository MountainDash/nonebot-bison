import httpx
import json
import time
from collections import defaultdict
from bs4 import BeautifulSoup as bs
from datetime import datetime
from nonebot import logger

from ..utils import Singleton, Render
from ..post import Post

class Arknights(metaclass=Singleton):
    
    def __init__(self):
        self.exists_posts = defaultdict(set)
        self.inited = defaultdict(lambda: False)

    async def get_announce_list(self):
        async with httpx.AsyncClient() as client:
            raw_data = await client.get('http://ak-fs.hypergryph.com/announce/IOS/announcement.meta.json')
            return json.loads(raw_data.text)

    async def filter(self, announce_data, inited=False) -> list[Post]:
        announce_list = announce_data['announceList']
        res: list[Post] = []
        for announce in announce_list:
            if inited:
                self.exists_posts['default'].add(announce['announceId'])
                continue
            if announce['announceId'] in self.exists_posts['default']:
                continue
            res.append(await self.parse(announce['webUrl']))
            self.exists_posts['default'].add(announce['announceId'])
        if None in res:
            res.remove(None)
        return res

    async def parse(self, announce_url: str) -> Post:
        async with httpx.AsyncClient() as client:
            raw_html = await client.get(announce_url)
        soup = bs(raw_html, 'html.parser')
        pics = []
        if soup.find("div", class_="standerd-container"):
            # 图文
            render = Render()
            viewport = {'width': 320, 'height': 6400, 'deviceScaleFactor': 3}
            pic_data = await render.render(announce_url, viewport=viewport, target='div.main')
            pics.append('base64://{}'.format(pic_data))
        elif (pic := soup.find('img', class_='banner-image')):
            pics.append(pic['src'])
        else:
            return None
        return Post('arknights', '', announce_url, pics=pics)
    
    async def fetch_new_post(self, _) -> list[Post]:
        try:
            data = await self.get_announce_list()
            if self.inited['default']:
                return await self.filter(data)
            else:
                await self.filter(data, True)
                self.inited['default'] = True
                return []
        except httpx.RequestError as err:
            logger.warning("network connection error: {}, url: {}".format(type(err), err.request.url))
            return []

