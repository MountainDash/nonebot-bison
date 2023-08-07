from typing import Any

from httpx import AsyncClient
from bs4 import BeautifulSoup as bs

from ..cards import card_manager
from ..post import CardPost, PlainPost
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

    async def parse(self, raw_post: RawPost) -> CardPost | PlainPost:
        raw_data = await self.client.get(
            f"https://ak-webview.hypergryph.com/api/game/bulletin/{self.get_id(post=raw_post)}"
        )
        raw_data = raw_data.json()["data"]

        announce_title = raw_data.get("header") if raw_data.get("header") != "" else raw_data.get("title")
        text = ""

        pics = []
        if raw_data["bannerImageUrl"]:
            pics.append(raw_post["bannerImageUrl"])

        elif raw_data["content"]:
            require("nonebot_plugin_htmlrender")
            from nonebot_plugin_htmlrender import template_to_pic

            template_path = str(Path(__file__).parent.parent / "post/templates/ark_announce")
            pic_data = await template_to_pic(
                template_path=template_path,
                template_name="index.html",
                templates={
                    "bannerImageUrl": raw_data["bannerImageUrl"],
                    "announce_title": announce_title,
                    "content": raw_data["content"],
                },
                pages={
                    "viewport": {"width": 400, "height": 100},
                    "base_url": f"file://{template_path}",
                },
            )
            # render = Render()
            # viewport = {"width": 320, "height": 6400, "deviceScaleFactor": 3}
            # pic_data = await render.render(
            #     announce_url, viewport=viewport, target="div.main"
            # )
            if pic_data:
                pics.append(pic_data)
            else:
                text = "图片渲染失败"
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

    def _gen_post(self, text: str) -> PlainPost:
        return PlainPost(
            "arknights",
            text=text,
            target_name="明日方舟更新信息",
        )

    def compare_status(self, _, old_status, new_status):
        res = []
        if old_status.get("preAnnounceType") == 2 and new_status.get("preAnnounceType") == 0:
            res.append(self._gen_post("登录界面维护公告上线（大概是开始维护了)"))
        elif old_status.get("preAnnounceType") == 0 and new_status.get("preAnnounceType") == 2:
            res.append(self._gen_post("登录界面维护公告下线（大概是开服了，冲！）"))

        if old_status.get("clientVersion") != new_status.get("clientVersion"):
            res.append(self._gen_post("游戏本体更新（大更新）"))
        if old_status.get("resVersion") != new_status.get("resVersion"):
            res.append(self._gen_post("游戏资源更新（小更新）"))

        return res

    def get_category(self, _):
        return Category(2)

    async def parse(self, raw_post):
        return raw_post


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

    async def parse(self, raw_post: RawPost) -> PlainPost:
        url = f'https://monster-siren.hypergryph.com/info/{raw_post["cid"]}'
        res = await self.client.get(f'https://monster-siren.hypergryph.com/api/news/{raw_post["cid"]}')
        raw_data = res.json()
        content = raw_data["data"]["content"]
        content = content.replace("</p>", "</p>\n")
        soup = bs(content, "html.parser")
        imgs = [x["src"] for x in soup("img")]
        text = f'{raw_post["title"]}\n{soup.text.strip()}'
        return PlainPost(
            "monster-siren",
            text=text,
            pics=imgs,
            url=url,
            target_name="塞壬唱片新闻",
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

    async def parse(self, raw_post: RawPost) -> PlainPost:
        url = f'https://terra-historicus.hypergryph.com/comic/{raw_post["comicCid"]}/episode/{raw_post["episodeCid"]}'
        return PlainPost(
            "terra-historicus",
            text=f'{raw_post["title"]} - {raw_post["episodeShortTitle"]}',
            pics=[raw_post["coverUrl"]],
            url=url,
            target_name="泰拉记事社漫画",
            compress=True,
        )
