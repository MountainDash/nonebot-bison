from datetime import datetime
import hashlib
import json
import re
from typing import Any, Optional

from bs4 import BeautifulSoup as bs
import httpx

from ..post import Post
from ..types import *
# from .platform import Platform


# class Wechat(Platform):

#     categories = {}
#     enable_tag = False
#     platform_name = 'wechat'
#     enabled = False
#     is_common = False
#     name = '微信公众号'

#     @classmethod
#     def _get_query_url(cls, target: Target):
#         return 'https://weixin.sogou.com/weixin?type=1&s_from=input&query={}&ie=utf8&_sug_=n&_sug_type_='.format(target)

#     @classmethod
#     async def _get_target_soup(cls, target: Target) -> Optional[bs]:
#         target_url = cls._get_query_url(target)
#         async with httpx.AsyncClient() as client:
#             res = await client.get(target_url)
#         soup = bs(res.text, 'html.parser')
#         blocks = soup.find(class_='news-list2').find_all('li',recursive=False)
#         for block in blocks:
#             if block.find(string=[target]):
#                 return block

#     @classmethod
#     async def get_account_name(cls, target: Target) -> Optional[str]:
#         if not (block := await cls._get_target_soup(target)):
#             return None
#         return block.find('p', class_='tit').find('a').text

#     async def get_sub_list(self, target: Target) -> list[RawPost]:
#         block = await self._get_target_soup(target)
#         if (last_post_dt := block.find('dt', string='最近文章：')):
#             post = {
#                     'title': last_post_dt.find_parent().find('a').text,
#                     'target': target,
#                     'page_url': self._get_query_url(target),
#                     'name': block.find('p', class_='tit').find('a').text
#                     }
#             return [post]
#         else:
#             return []

#     def get_id(self, post: RawPost) -> Any:
#         return post['title']

#     def get_date(self, post: RawPost):
#         return None

#     def get_tags(self, post: RawPost):
#         return None

#     def get_category(self, post: RawPost):
#         return None

#     async def parse(self, raw_post: RawPost) -> Post:
#         # TODO get content of post
#         return Post(target_type='wechat',
#                 text='{}\n详细内容请自行查看公众号'.format(raw_post['title']),
#                 target_name=raw_post['name'],
#                 pics=[],
#                 url=''
#                 )

