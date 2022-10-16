import json
from typing import Any, Optional

from bs4 import BeautifulSoup as bs
from httpx import AsyncClient
from nonebot.plugin import require

from ..post import Post
from ..types import Category, RawPost, Target
from ..utils.scheduler_config import SchedulerConfig
from .platform import CategoryNotSupport, NewMessage, StatusChange


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
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        return "明日方舟游戏信息"

    async def get_sub_list(self, _) -> list[RawPost]:
        raw_data = await self.client.get(
            "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/announcement.meta.json"
        )
        return json.loads(raw_data.text)["announceList"]

    def get_id(self, post: RawPost) -> Any:
        return post["announceId"]

    def get_date(self, _: RawPost) -> None:
        return None

    def get_category(self, _) -> Category:
        return Category(1)

    async def parse(self, raw_post: RawPost) -> Post:
        announce_url = raw_post["webUrl"]
        text = ""
        raw_html = await self.client.get(announce_url)
        soup = bs(raw_html.text, "html.parser")
        pics = []
        if soup.find("div", class_="standerd-container"):
            # 图文
            require("nonebot_plugin_htmlrender")
            from nonebot_plugin_htmlrender import capture_element

            pic_data = await capture_element(
                announce_url,
                "div.main",
                viewport={"width": 320, "height": 6400},
                device_scale_factor=3,
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
        elif pic := soup.find("img", class_="banner-image"):
            pics.append(pic["src"])  # type: ignore
        else:
            raise CategoryNotSupport()
        return Post(
            "arknights",
            text=text,
            url="",
            target_name="明日方舟游戏内公告",
            pics=pics,
            compress=True,
            override_use_pic=False,
        )


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
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        return "明日方舟游戏信息"

    async def get_status(self, _):
        res_ver = await self.client.get(
            "https://ak-conf.hypergryph.com/config/prod/official/IOS/version"
        )
        res_preanounce = await self.client.get(
            "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json"
        )
        res = res_ver.json()
        res.update(res_preanounce.json())
        return res

    def compare_status(self, _, old_status, new_status):
        res = []
        if (
            old_status.get("preAnnounceType") == 2
            and new_status.get("preAnnounceType") == 0
        ):
            res.append(
                Post("arknights", text="登录界面维护公告上线（大概是开始维护了)", target_name="明日方舟更新信息")
            )
        elif (
            old_status.get("preAnnounceType") == 0
            and new_status.get("preAnnounceType") == 2
        ):
            res.append(
                Post("arknights", text="登录界面维护公告下线（大概是开服了，冲！）", target_name="明日方舟更新信息")
            )
        if old_status.get("clientVersion") != new_status.get("clientVersion"):
            res.append(Post("arknights", text="游戏本体更新（大更新）", target_name="明日方舟更新信息"))
        if old_status.get("resVersion") != new_status.get("resVersion"):
            res.append(Post("arknights", text="游戏资源更新（小更新）", target_name="明日方舟更新信息"))
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
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        return "明日方舟游戏信息"

    async def get_sub_list(self, _) -> list[RawPost]:
        raw_data = await self.client.get(
            "https://monster-siren.hypergryph.com/api/news"
        )
        return raw_data.json()["data"]["list"]

    def get_id(self, post: RawPost) -> Any:
        return post["cid"]

    def get_date(self, _) -> None:
        return None

    def get_category(self, _) -> Category:
        return Category(3)

    async def parse(self, raw_post: RawPost) -> Post:
        url = f'https://monster-siren.hypergryph.com/info/{raw_post["cid"]}'
        res = await self.client.get(
            f'https://monster-siren.hypergryph.com/api/news/{raw_post["cid"]}'
        )
        raw_data = res.json()
        content = raw_data["data"]["content"]
        content = content.replace("</p>", "</p>\n")
        soup = bs(content, "html.parser")
        imgs = list(map(lambda x: x["src"], soup("img")))
        text = f'{raw_post["title"]}\n{soup.text.strip()}'
        return Post(
            "monster-siren",
            text=text,
            pics=imgs,
            url=url,
            target_name="塞壬唱片新闻",
            compress=True,
            override_use_pic=False,
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
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        return "明日方舟游戏信息"

    async def get_sub_list(self, _) -> list[RawPost]:
        raw_data = await self.client.get(
            "https://terra-historicus.hypergryph.com/api/recentUpdate"
        )
        return raw_data.json()["data"]

    def get_id(self, post: RawPost) -> Any:
        return f'{post["comicCid"]}/{post["episodeCid"]}'

    def get_date(self, _) -> None:
        return None

    def get_category(self, _) -> Category:
        return Category(4)

    async def parse(self, raw_post: RawPost) -> Post:
        url = f'https://terra-historicus.hypergryph.com/comic/{raw_post["comicCid"]}/episode/{raw_post["episodeCid"]}'
        return Post(
            "terra-historicus",
            text=f'{raw_post["title"]} - {raw_post["episodeShortTitle"]}',
            pics=[raw_post["coverUrl"]],
            url=url,
            target_name="泰拉记事社漫画",
            compress=True,
            override_use_pic=False,
        )
