from typing import Any
import httpx
import json
from bs4 import BeautifulSoup as bs

from ..types import Category, RawPost, Target

from .platform import NewMessage, NoTargetMixin, CategoryNotSupport, StatusChange

from ..utils import Render
from ..post import Post


class Arknights(NewMessage, NoTargetMixin):

    categories = {1: '游戏公告'}
    platform_name = 'arknights'
    name = '明日方舟游戏信息'
    enable_tag = False
    enabled = True
    is_common = False
    schedule_type = 'interval'
    schedule_kw = {'seconds': 30}

    async def get_target_name(self, _: Target) -> str:
        return '明日方舟游戏信息'

    async def get_sub_list(self, _) -> list[RawPost]:
        async with httpx.AsyncClient() as client:
            raw_data = await client.get('https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/announcement.meta.json')
            return json.loads(raw_data.text)['announceList']

    def get_id(self, post: RawPost) -> Any:
        return post['announceId']

    def get_date(self, _: RawPost) -> None:
        return None

    def get_category(self, _) -> Category:
        return Category(1)

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
            pics.append(pic_data)
        elif (pic := soup.find('img', class_='banner-image')):
            pics.append(pic['src'])
        else:
            raise CategoryNotSupport()
        return Post('arknights', text='', url='', target_name="明日方舟游戏内公告", pics=pics, compress=True, override_use_pic=False)

class AkVersion(NoTargetMixin, StatusChange):

    categories = {2: '更新信息'}
    platform_name = 'arknights'
    name = '明日方舟游戏信息'
    enable_tag = False
    enabled = True
    is_common = False
    schedule_type = 'interval'
    schedule_kw = {'seconds': 30}

    async def get_target_name(self, _: Target) -> str:
        return '明日方舟游戏信息'

    async def get_status(self, _):
        async with httpx.AsyncClient() as client:
            res_ver = await client.get('https://ak-conf.hypergryph.com/config/prod/official/IOS/version')
            res_preanounce = await client.get('https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json')
        res = res_ver.json()
        res.update(res_preanounce.json())
        return res

    def compare_status(self, _, old_status, new_status):
        res = []
        if old_status.get('preAnnounceType') == 2 and new_status.get('preAnnounceType') == 0:
            res.append(Post('arknights', text='开始维护！', target_name='明日方舟更新信息'))
        elif old_status.get('preAnnounceType') == 0 and new_status.get('preAnnounceType') == 2:
            res.append(Post('arknights', text='维护结束！冲！（可能不太准确）', target_name='明日方舟更新信息'))
        if old_status.get('clientVersion') != new_status.get('clientVersion'):
            res.append(Post('arknights', text='游戏本体更新（大更新）', target_name='明日方舟更新信息'))
        if old_status.get('resVersion') != new_status.get('resVersion'):
            res.append(Post('arknights', text='游戏资源更新（小更新）', target_name='明日方舟更新信息'))
        return res

    def get_category(self, _):
        return Category(2)

    async def parse(self, raw_post):
        return raw_post
