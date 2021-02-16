from collections import defaultdict
from datetime import datetime
import json
import time
from typing import Any, Optional

from bs4 import BeautifulSoup as bs
import httpx
from nonebot import logger

from ..post import Post
from ..types import *
from ..utils import Singleton
from .platform import Platform

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
