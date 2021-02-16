import httpx
import json
import time
from collections import defaultdict
from bs4 import BeautifulSoup as bs
from datetime import datetime
from nonebot import logger
from typing import Any, Optional

from ..utils import Singleton
from ..post import Post
from ..types import *
from .platform import Platform

class Weibo_(metaclass=Singleton):

    def __init__(self):
        self.exists_posts = defaultdict(set)
        self.inited = defaultdict(lambda: False)

    async def get_user_post_list(self, weibo_id: str):
        async with httpx.AsyncClient() as client:
            params = { 'containerid': '107603' + weibo_id}
            res = await client.get('https://m.weibo.cn/api/container/getIndex?', params=params, timeout=4.0)
            return res.text

    def filter_weibo(self, weibo_raw_text, target, init=False):
        weibo_dict = json.loads(weibo_raw_text)
        weibos = weibo_dict['data']['cards']
        res: list[Post] = []
        for weibo in weibos:
            if weibo['card_type'] != 9:
                continue
            info = weibo['mblog']
            if init:
                self.exists_posts[target].add(info['id'])
                continue
            if info['id'] in self.exists_posts[target]:
                continue
            created_time = datetime.strptime(info['created_at'], '%a %b %d %H:%M:%S %z %Y')
            if time.time() - created_time.timestamp() > 60 * 60 * 2:
                continue
            res.append(self.parse_weibo(weibo, target))
        return res

    def parse_weibo(self, weibo_dict, target):
        info = weibo_dict['mblog']
        parsed_text = bs(info['text'], 'html.parser').text
        pic_urls = [img['large']['url'] for img in info.get('pics', [])]
        self.exists_posts[target].add(info['id'])
        detail_url = 'https://weibo.com/{}/{}'.format(info['user']['id'], info['bid'])
        # return parsed_text, detail_url, pic_urls
        return Post('weibo', parsed_text, detail_url, pic_urls)

    async def fetch_new_post(self, target):
        try:
            post_list = await self.get_user_post_list(target)
            if not self.inited[target]:
                self.filter_weibo(post_list, target, True)
                logger.info('weibo init {} success'.format(target))
                logger.info('post list: {}'.format(self.exists_posts[target]))
                self.inited[target] = True
                return []
            return self.filter_weibo(post_list, target)
        except httpx.RequestError as err:
            logger.warning("network connection error: {}, url: {}".format(type(err), err.request.url))
            return []

async def get_user_info(id):
    async with httpx.AsyncClient() as client:
        param = {'containerid': '100505' + id}
        res = await client.get('https://m.weibo.cn/api/container/getIndex', params=param)
        res_dict = json.loads(res.text)
        if res_dict.get('ok') == 1:
            return res_dict['data']['userInfo']['screen_name']
        else:
            return None

class Weibo(Platform):

    categories = {
            1: '转发',
            2: '视频',
            3: '图文'
        }
    enable_tag = False
    platform_name = 'weibo'

    @staticmethod
    async def get_account_name(target: Target) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            param = {'containerid': '100505' + target}
            res = await client.get('https://m.weibo.cn/api/container/getIndex', params=param)
            res_dict = json.loads(res.text)
            if res_dict.get('ok') == 1:
                return res_dict['data']['userInfo']['screen_name']
            else:
                return None

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        async with httpx.AsyncClient() as client:
            params = { 'containerid': '107603' + target}
            res = await client.get('https://m.weibo.cn/api/container/getIndex?', params=params, timeout=4.0)
            res_data = json.loads(res.text)
            if not res_data['ok']:
                return []
            return res_data['data']['cards']

    def get_id(self, post: RawPost) -> Any:
        return post['mblog']['id']

    def filter_platform_custom(self, raw_post: RawPost) -> bool:
        return raw_post['card_type'] == 9

    def get_date(self, raw_post: RawPost) -> float:
        created_time = datetime.strptime(raw_post['mblog']['created_at'], '%a %b %d %H:%M:%S %z %Y')
        return created_time.timestamp()

    def get_tags(self, raw_post: RawPost) -> Optional[list[Tag]]:
        "Return Tag list of given RawPost"
        return None

    def get_category(self, raw_post: RawPost) -> Category:
        if raw_post['mblog'].get('retweeted_status'):
            return Category(1)
        elif raw_post['mblog'].get('page_info') and raw_post['mblog']['page_info'].get('type') == 'video':
            return Category(2)
        else:
            return Category(3)
 
    async def parse(self, raw_post: RawPost) -> Post:
        info = raw_post['mblog']
        parsed_text = bs(info['text'], 'html.parser').text
        pic_urls = [img['large']['url'] for img in info.get('pics', [])]
        detail_url = 'https://weibo.com/{}/{}'.format(info['user']['id'], info['bid'])
        # return parsed_text, detail_url, pic_urls
        return Post('weibo', parsed_text, detail_url, pic_urls)
