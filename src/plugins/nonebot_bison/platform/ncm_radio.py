from typing import Any, Optional

import httpx

from ..post import Post
from ..types import RawPost, Target
from .platform import NewMessage


class NcmRadio(NewMessage):

    categories = {}
    platform_name = "ncm-radio"
    enable_tag = False
    enabled = True
    is_common = False
    schedule_type = "interval"
    schedule_kw = {"minutes": 10}
    name = "网易云-电台"
    has_target = True

    async def get_target_name(self, target: Target) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "http://music.163.com/api/dj/program/byradio",
                headers={"Referer": "https://music.163.com/"},
                data={"radioId": target, "limit": 1000, "offset": 0},
            )
            res_data = res.json()
            if res_data["code"] != 200 or res_data["programs"] == 0:
                return
            return res_data["programs"][0]["radio"]["name"]

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "http://music.163.com/api/dj/program/byradio",
                headers={"Referer": "https://music.163.com/"},
                data={"radioId": target, "limit": 1000, "offset": 0},
            )
            res_data = res.json()
            if res_data["code"] != 200:
                return []
            else:
                return res_data["programs"]

    def get_id(self, post: RawPost) -> Any:
        return post["id"]

    def get_date(self, post: RawPost) -> int:
        return post["createTime"] // 1000

    async def parse(self, raw_post: RawPost) -> Post:
        text = "网易云电台更新：{}".format(raw_post["name"])
        target_name = raw_post["radio"]["name"]
        pics = [raw_post["coverUrl"]]
        url = "https://music.163.com/#/program/{}".format(raw_post["id"])
        return Post("ncm-radio", text=text, url=url, pics=pics, target_name=target_name)
