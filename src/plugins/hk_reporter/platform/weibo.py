import httpx
import json
import time
from collections import defaultdict
from bs4 import BeautifulSoup as bs
from datetime import datetime
from nonebot import logger

from ..utils import Singleton
from ..post import Post

class Weibo(metaclass=Singleton):

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
