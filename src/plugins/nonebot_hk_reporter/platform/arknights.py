from typing import Any
import httpx
import json
import time
from collections import defaultdict
from bs4 import BeautifulSoup as bs
from datetime import datetime
from nonebot import logger

from ..types import Category, RawPost, Tag, Target

from .platform import PlatformNoTarget, CategoryNotSupport

from ..utils import Singleton, Render
from ..post import Post


class Arknights(PlatformNoTarget):

    categories = {}
    platform_name = 'arknights'
    name = '明日方舟游戏内公告'
    enable_tag = False
    enabled = True
    is_common = False
    schedule_interval = 30

    @staticmethod
    async def get_account_name(_: Target) -> str:
        return '明日方舟游戏内公告'

    async def get_sub_list(self) -> list[RawPost]:
        async with httpx.AsyncClient() as client:
            raw_data = await client.get('http://ak-fs.hypergryph.com/announce/IOS/announcement.meta.json')
            return json.loads(raw_data.text)['announceList']

    def get_id(self, post: RawPost) -> Any:
        return post['announceId']

    def get_date(self, post: RawPost) -> None:
        return None

    async def parse(self, raw_post: RawPost) -> Post:
        announce_url = raw_post['webUrl']
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
            raise CategoryNotSupport()
        return Post('arknights', text='', url='', target_name="明日方舟游戏内公告", pics=pics, compress=True, override_use_pic=False)
