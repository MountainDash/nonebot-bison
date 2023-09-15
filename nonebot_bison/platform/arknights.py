from typing import Any

from httpx import AsyncClient
from bs4 import BeautifulSoup as bs

from ..post import Post
from ..card.themes import ArkStem, PlainStem
from ..types import Target, RawPost, Category
from ..utils.scheduler_config import SchedulerConfig
from .platform import NewMessage, StatusChange, CategoryNotRecognize


class ArknightsSchedConf(SchedulerConfig):
    name = "arknights"
    schedule_type = "interval"
    schedule_setting = {"seconds": 30}


class Arknights(NewMessage):
    categories = {1: "游戏公告"}
    platform_name = "arknights"
    name = "明日方舟游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    scheduler = ArknightsSchedConf
    has_target = False

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "明日方舟游戏信息"

    async def get_sub_list(self, _) -> list[RawPost]:
        raw_data = await self.client.get("https://ak-webview.hypergryph.com/api/game/bulletinList?target=IOS")
        return raw_data.json()["data"]["list"]

    def get_id(self, post: RawPost) -> Any:
        return post["cid"]

    def get_date(self, _: RawPost) -> Any:
        return None

    def get_category(self, _) -> Category:
        return Category(1)

    async def plain_parse(self, raw_post: RawPost) -> Post:
        raw_data = await self.client.get(
            f"https://ak-webview.hypergryph.com/api/game/bulletin/{self.get_id(post=raw_post)}"
        )
        raw_data = raw_data.json()["data"]

        announce_title = raw_data.get("header") if raw_data.get("header") != "" else raw_data.get("title")

        pics = []
        if raw_data["bannerImageUrl"]:
            pics.append(raw_post["bannerImageUrl"])
            return Post(
                PlainStem(
                    platform="arknights",
                    text=announce_title,
                    target_name="明日方舟游戏内公告",
                ),
                pics=pics,
                compress=True,
            )

        elif content := raw_data["content"]:
            html = bs(content, "html.parser")
            sep = "\n"
            text = f"{announce_title}\n{html.get_text(separator=sep)}"
            return Post(
                PlainStem(
                    platform="arknights",
                    text=text,
                    target_name="明日方舟游戏内公告",
                ),
                pics=raw_post.get("bannerImageUrl", []),
                compress=True,
            )
        else:
            raise CategoryNotRecognize("未找到可渲染部分")

    async def arknights_parse(self, raw_post: RawPost) -> Post:
        raw_data = await self.client.get(
            f"https://ak-webview.hypergryph.com/api/game/bulletin/{self.get_id(post=raw_post)}"
        )
        raw_data = raw_data.json()["data"]

        announce_title = raw_data.get("header") if raw_data.get("header") != "" else raw_data.get("title")

        pics = []
        if raw_data["bannerImageUrl"]:
            pics.append(raw_post["bannerImageUrl"])
            return Post(
                ArkStem(announce_title=announce_title, banner_image_url=raw_data["bannerImageUrl"], content=""),
                pics=pics,
                compress=True,
            )

        elif raw_data["content"]:
            return Post(
                ArkStem(
                    announce_title=announce_title,
                    banner_image_url=raw_data.get("bannerImageUrl", []),
                    content=raw_data["content"],
                ),
                pics=pics,
            )
        else:
            raise CategoryNotRecognize("未找到可渲染部分")


class AkVersion(StatusChange):
    categories = {2: "更新信息"}
    platform_name = "arknights"
    name = "明日方舟游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    scheduler = ArknightsSchedConf
    has_target = False

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "明日方舟游戏信息"

    async def get_status(self, _):
        res_ver = await self.client.get("https://ak-conf.hypergryph.com/config/prod/official/IOS/version")
        res_preanounce = await self.client.get(
            "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json"
        )
        res = res_ver.json()
        res.update(res_preanounce.json())
        return res

    def compare_status(self, _, old_status, new_status):
        res = []

        if old_status.get("preAnnounceType") == 2 and new_status.get("preAnnounceType") == 0:
            res.append(self.post_maker("登录界面维护公告上线（大概是开始维护了)"))
        elif old_status.get("preAnnounceType") == 0 and new_status.get("preAnnounceType") == 2:
            res.append(self.post_maker("登录界面维护公告下线（大概是开服了，冲！）"))
        if old_status.get("clientVersion") != new_status.get("clientVersion"):
            res.append(self.post_maker("游戏本体更新（大更新）"))
        if old_status.get("resVersion") != new_status.get("resVersion"):
            res.append(self.post_maker("游戏资源更新（小更新）"))
        return res

    def get_category(self, _):
        return Category(2)

    async def plain_parse(self, raw_post):
        return raw_post

    @staticmethod
    def post_maker(text: str):
        return Post(
            PlainStem(
                platform="arknights",
                text=text,
                target_name="明日方舟更新信息",
            ),
        )


class MonsterSiren(NewMessage):
    categories = {3: "塞壬唱片新闻"}
    platform_name = "arknights"
    name = "明日方舟游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    scheduler = ArknightsSchedConf
    has_target = False

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "明日方舟游戏信息"

    async def get_sub_list(self, _) -> list[RawPost]:
        raw_data = await self.client.get("https://monster-siren.hypergryph.com/api/news")
        return raw_data.json()["data"]["list"]

    def get_id(self, post: RawPost) -> Any:
        return post["cid"]

    def get_date(self, _) -> None:
        return None

    def get_category(self, _) -> Category:
        return Category(3)

    async def plain_parse(self, raw_post: RawPost) -> Post:
        url = f'https://monster-siren.hypergryph.com/info/{raw_post["cid"]}'
        res = await self.client.get(f'https://monster-siren.hypergryph.com/api/news/{raw_post["cid"]}')
        raw_data = res.json()
        content = raw_data["data"]["content"]
        content = content.replace("</p>", "</p>\n")
        soup = bs(content, "html.parser")
        imgs = [x["src"] for x in soup("img")]
        text = f'{raw_post["title"]}\n{soup.text.strip()}'
        return Post(
            PlainStem(
                platform="monster-siren",
                text=text,
                url=url,
                target_name="塞壬唱片新闻",
            ),
            pics=imgs,
            compress=True,
        )


class TerraHistoricusComic(NewMessage):
    categories = {4: "泰拉记事社漫画"}
    platform_name = "arknights"
    name = "明日方舟游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    scheduler = ArknightsSchedConf
    has_target = False

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "明日方舟游戏信息"

    async def get_sub_list(self, _) -> list[RawPost]:
        raw_data = await self.client.get("https://terra-historicus.hypergryph.com/api/recentUpdate")
        return raw_data.json()["data"]

    def get_id(self, post: RawPost) -> Any:
        return f'{post["comicCid"]}/{post["episodeCid"]}'

    def get_date(self, _) -> None:
        return None

    def get_category(self, _) -> Category:
        return Category(4)

    async def plain_parse(self, raw_post: RawPost) -> Post:
        url = f'https://terra-historicus.hypergryph.com/comic/{raw_post["comicCid"]}/episode/{raw_post["episodeCid"]}'
        return Post(
            PlainStem(
                platform="terra-historicus",
                text=f'{raw_post["title"]} - {raw_post["episodeShortTitle"]}',
                url=url,
                target_name="泰拉记事社漫画",
            ),
            pics=[raw_post["coverUrl"]],
            compress=True,
        )
