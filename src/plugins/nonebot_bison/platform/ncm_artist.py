import re
from typing import Any, Optional

from ..post import Post
from ..types import RawPost, Target
from ..utils import SchedulerConfig, http_client
from .platform import NewMessage


class NcmSchedConf(SchedulerConfig, name="music.163.com"):

    schedule_type = "interval"
    schedule_setting = {"minutes": 1}


class NcmArtist(NewMessage):

    categories = {}
    platform_name = "ncm-artist"
    enable_tag = False
    enabled = True
    is_common = True
    scheduler_class = "music.163.com"
    name = "网易云-歌手"
    has_target = True
    parse_target_promot = "请输入歌手主页（包含数字ID）的链接"

    async def get_target_name(self, target: Target) -> Optional[str]:
        async with http_client() as client:
            res = await client.get(
                "https://music.163.com/api/artist/albums/{}".format(target),
                headers={"Referer": "https://music.163.com/"},
            )
            res_data = res.json()
            if res_data["code"] != 200:
                return
            return res_data["artist"]["name"]

    async def parse_target(self, target_text: str) -> Target:
        if re.match(r"^\d+$", target_text):
            return Target(target_text)
        elif match := re.match(
            r"(?:https?://)?music\.163\.com/#/artist\?id=(\d+)", target_text
        ):
            return Target(match.group(1))
        else:
            raise self.ParseTargetException()

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        async with http_client() as client:
            res = await client.get(
                "https://music.163.com/api/artist/albums/{}".format(target),
                headers={"Referer": "https://music.163.com/"},
            )
            res_data = res.json()
            if res_data["code"] != 200:
                return []
            else:
                return res_data["hotAlbums"]

    def get_id(self, post: RawPost) -> Any:
        return post["id"]

    def get_date(self, post: RawPost) -> int:
        return post["publishTime"] // 1000

    async def parse(self, raw_post: RawPost) -> Post:
        text = "新专辑发布：{}".format(raw_post["name"])
        target_name = raw_post["artist"]["name"]
        pics = [raw_post["picUrl"]]
        url = "https://music.163.com/#/album?id={}".format(raw_post["id"])
        return Post(
            "ncm-artist", text=text, url=url, pics=pics, target_name=target_name
        )
