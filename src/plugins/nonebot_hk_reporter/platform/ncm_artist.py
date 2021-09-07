from typing import Any, Optional

import httpx
from ..post import Post
from ..types import RawPost, Target
from .platform import TargetMixin, NewMessage

class NcmArtist(TargetMixin, NewMessage):

    categories = {}
    platform_name = 'ncm-artist'
    enable_tag = False
    enabled = True
    is_common = True
    schedule_type = 'interval'
    schedule_kw = {'minutes': 10}
    name = "网易云-歌手"

    async def get_target_name(self, target: Target) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                    "https://music.163.com/api/artist/albums/{}".format(target),
                    headers={'Referer': 'https://music.163.com/'}
                    )
            res_data = res.json()
            if res_data['code'] != 200:
                return
            return res_data['artist']['name']

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                    "https://music.163.com/api/artist/albums/{}".format(target),
                    headers={'Referer': 'https://music.163.com/'}
                    )
            res_data = res.json()
            if res_data['code'] != 200:
                return []
            else:
                return res_data['hotAlbums']

    def get_id(self, post: RawPost) -> Any:
        return post['id']

    def get_date(self, post: RawPost) -> int:
        return post['publishTime'] // 1000

    async def parse(self, raw_post: RawPost) -> Post:
        text = '新专辑发布：{}'.format(raw_post['name'])
        target_name = raw_post['artist']['name']
        pics = [raw_post['picUrl']]
        url = "https://music.163.com/#/album?id={}".format(raw_post['id'])
        return Post('ncm-artist', text=text, url=url, pics=pics, target_name=target_name)
