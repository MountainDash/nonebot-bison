import re
from typing import Any, ClassVar

from httpx import AsyncClient

from nonebot_bison.post import Post
from nonebot_bison.types import ApiError, Category, RawPost, Target
from nonebot_bison.utils import Site

from .platform import NewMessage


class NcmSite(Site):
    name = "music.163.com"
    schedule_type = "interval"
    schedule_setting: ClassVar[dict] = {"minutes": 1}


class NcmArtist(NewMessage):
    categories: ClassVar[dict[Category, str]] = {}
    platform_name = "ncm-artist"
    enable_tag = False
    enabled = True
    is_common = True
    site = NcmSite
    name = "网易云-歌手"
    has_target = True
    parse_target_promot = "请输入歌手主页（包含数字ID）的链接"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        res = await client.get(
            f"https://music.163.com/api/artist/albums/{target}",
            headers={"Referer": "https://music.163.com/"},
        )
        res_data = res.json()
        if res_data["code"] != 200:
            raise ApiError(res.request.url)
        return res_data["artist"]["name"]

    @classmethod
    async def parse_target(cls, target_text: str) -> Target:
        if re.match(r"^\d+$", target_text):
            return Target(target_text)
        elif match := re.match(r"(?:https?://)?music\.163\.com/#/artist\?id=(\d+)", target_text):
            return Target(match.group(1))
        else:
            raise cls.ParseTargetException("正确格式:\n1. 歌手数字ID\n2. https://music.163.com/#/artist?id=xxxx")

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        client = await self.ctx.get_client()
        res = await client.get(
            f"https://music.163.com/api/artist/albums/{target}",
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
        return Post(self, content=text, url=url, images=pics, nickname=target_name)


class NcmRadio(NewMessage):
    categories: ClassVar[dict[Category, str]] = {}
    platform_name = "ncm-radio"
    enable_tag = False
    enabled = True
    is_common = False
    site = NcmSite
    name = "网易云-电台"
    has_target = True
    parse_target_promot = "请输入主播电台主页（包含数字ID）的链接"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        res = await client.post(
            "http://music.163.com/api/dj/program/byradio",
            headers={"Referer": "https://music.163.com/"},
            data={"radioId": target, "limit": 1000, "offset": 0},
        )
        res_data = res.json()
        if res_data["code"] != 200 or res_data["programs"] == 0:
            return
        return res_data["programs"][0]["radio"]["name"]

    @classmethod
    async def parse_target(cls, target_text: str) -> Target:
        if re.match(r"^\d+$", target_text):
            return Target(target_text)
        elif match := re.match(r"(?:https?://)?music\.163\.com/#/djradio\?id=(\d+)", target_text):
            return Target(match.group(1))
        else:
            raise cls.ParseTargetException(
                prompt="正确格式:\n1. 电台数字ID\n2. https://music.163.com/#/djradio?id=xxxx"
            )

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        client = await self.ctx.get_client()
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
        return Post(self, content=text, url=url, images=pics, nickname=target_name)
