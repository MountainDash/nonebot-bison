from ..utils import Singleton
from ..post import Post
from collections import defaultdict
from nonebot import logger
import httpx
import json
import time

class Bilibili(metaclass=Singleton):
    
    def __init__(self):
        self.exists_posts = defaultdict(set)
        self.inited = defaultdict(lambda: False)

    async def get_user_post_list(self, user_id):
        async with httpx.AsyncClient() as client:
            params = {'host_uid': user_id, 'offset': 0, 'need_top': 0}
            res = await client.get('https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history', params=params, timeout=4.0)
            res_dict = json.loads(res.text)
            if res_dict['code'] == 0:
                return res_dict['data']

    def filter(self, data, target, init=False) -> list[Post]:
        cards = data['cards']
        res: list[Post] = []
        for card in cards:
            dynamic_id = card['desc']['dynamic_id']
            if init:
                self.exists_posts[target].add(dynamic_id)
                continue
            if dynamic_id in self.exists_posts[target]:
                continue
            if time.time() - card['desc']['timestamp'] > 60 * 60 * 2:
                continue
            res.append(self.parse(card, target))
        if None in res:
            res.remove(None)
        return res


    def parse(self, card, target) -> Post:
        card_content = json.loads(card['card'])
        dynamic_id = card['desc']['dynamic_id']
        self.exists_posts[target].add(dynamic_id)
        if card['desc']['type'] == 2:
            # 一般动态
            text = card_content['item']['description']
            url = 'https://t.bilibili.com/{}'.format(card['desc']['dynamic_id'])
            pic = [img['img_src'] for img in card_content['item']['pictures']]
        elif card['desc']['type'] == 64:
            # 专栏文章
            text = '{} {}'.format(card_content['title'], card_content['summary'])
            url = 'https://www.bilibili.com/read/cv{}'.format(card['desc']['rid'])
            pic = card_content['image_urls']
        elif card['desc']['type'] == 8:
            # 视频
            text = card_content['dynamic']
            url = 'https://www.bilibili.com/video/{}'.format(card['desc']['bvid'])
            pic = [card_content['pic']]
        elif card['desc']['type'] == 4:
            # 纯文字
            text = card_content['item']['content']
            url = 'https://t.bilibili.com/{}'.format(card['desc']['dynamic_id'])
            pic = []
        else:
            logger.error(card)
            return None
        return Post('bilibili', text, url, pic)

    async def fetch_new_post(self, target) -> list[Post]:
        try:
            post_list_data = await self.get_user_post_list(target)
            if self.inited[target]:
                return self.filter(post_list_data, target)
            else:
                self.filter(post_list_data, target, True)
                logger.info('bilibili init {} success'.format(target))
                logger.info('post list: {}'.format(self.exists_posts[target]))
                self.inited[target] = True
                return []
        except httpx.RequestError as err:
            logger.warning("network connection error: {}, url: {}".format(type(err), err.request.url))
            return []

async def get_user_info(mid):
    async with httpx.AsyncClient() as client:
        res = await client.get('https://api.bilibili.com/x/space/acc/info', params={'mid': mid})
        res_data = json.loads(res.text)
        if res_data['code']:
            return None
        return res_data['data']['name']
