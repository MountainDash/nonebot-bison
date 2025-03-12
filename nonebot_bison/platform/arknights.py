from functools import partial
import html
import re
from typing import Any, ClassVar

from bs4 import BeautifulSoup as bs
from httpx import AsyncClient
from nonebot.compat import type_validate_python
from pydantic import BaseModel, Field
from yarl import URL

from nonebot_bison.post import Post
from nonebot_bison.post.protocol import HTMLContentSupport
from nonebot_bison.types import Category, RawPost, Target
from nonebot_bison.utils import Site

from .platform import NewMessage, StatusChange


class ArkResponseBase(BaseModel):
    code: int
    msg: str


class BulletinListItem(BaseModel):
    cid: str
    title: str
    category: int
    display_time: str = Field(alias="displayTime")
    updated_at: int = Field(alias="updatedAt")
    sticky: bool


class BulletinList(BaseModel):
    list: list[BulletinListItem]


class BulletinData(BaseModel):
    cid: str
    display_type: int = Field(alias="displayType")
    title: str
    category: int
    header: str
    content: str
    jump_link: str = Field(alias="jumpLink")
    banner_image_url: str = Field(alias="bannerImageUrl")
    display_time: str = Field(alias="displayTime")
    updated_at: int = Field(alias="updatedAt")


class ArkBulletinListResponse(ArkResponseBase):
    data: BulletinList


class ArkBulletinResponse(ArkResponseBase):
    data: BulletinData


class ArknightsSite(Site):
    name = "arknights"
    schedule_type = "interval"
    schedule_setting: ClassVar[dict] = {"seconds": 30}


class ArknightsPost(Post, HTMLContentSupport):
    def _cleantext(self, text: str, old_split="\n", new_split="\n") -> str:
        """清理文本：去掉所有多余的空格和换行"""
        lines = text.strip().split(old_split)
        cleaned_lines = [line.strip() for line in lines if line != ""]
        return new_split.join(cleaned_lines)

    async def get_html_content(self) -> str:
        return self.content

    async def get_plain_content(self) -> str:
        content = html.unescape(self.content)  # 转义HTML特殊字符
        content = re.sub(
            r'\<p style="text-align:center;"\>(.*?)\<strong\>(.*?)\<span style=(.*?)\>(.*?)\<\/span\>(.*?)\<\/strong\>(.*?)<\/p\>',  # noqa: E501
            r"==\4==\n",
            content,
            flags=re.DOTALL,
        )  # 去“标题型”p
        content = re.sub(
            r'\<p style="text-align:(left|right);"?\>(.*?)\<\/p\>',
            r"\2\n",
            content,
            flags=re.DOTALL,
        )  # 去左右对齐的p
        content = re.sub(r"\<p\>(.*?)\</p\>", r"\1\n", content, flags=re.DOTALL)  # 去普通p
        content = re.sub(r'\<a href="(.*?)" target="_blank">(.*?)\<\/a\>', r"\1", content, flags=re.DOTALL)  # 去a
        content = re.sub(r"<br/>", "\n", content)  # 去br
        content = re.sub(r"\<strong\>(.*?)\</strong\>", r"\1", content)  # 去strong
        content = re.sub(r'<span style="color:(#.*?)">(.*?)</span>', r"\2", content)  # 去color
        content = re.sub(r'<div class="media-wrap image-wrap">(.*?)</div>', "", content)  # 去img
        return self._cleantext(content)


class Arknights(NewMessage):
    categories: ClassVar[dict[Category, str]] = {1: "游戏公告"}
    platform_name = "arknights"
    name = "明日方舟游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    site = ArknightsSite
    has_target = False
    default_theme = "arknights"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "明日方舟游戏信息"

    async def get_sub_list(self, _) -> list[BulletinListItem]:
        client = await self.ctx.get_client()
        raw_data = await client.get("https://ak-webview.hypergryph.com/api/game/bulletinList?target=IOS")
        return type_validate_python(ArkBulletinListResponse, raw_data.json()).data.list

    def get_id(self, post: BulletinListItem) -> Any:
        return post.cid

    def get_date(self, post: BulletinListItem) -> Any:
        # 为什么不使用post.updated_at？
        # update_at的时间是上传鹰角服务器的时间，而不是公告发布的时间
        # 也就是说鹰角可能会在中午就把晚上的公告上传到服务器，但晚上公告才会显示，但是update_at就是中午的时间不会改变
        # 如果指定了get_date，那么get_date会被优先使用, 并在获取到的值超过2小时时忽略这条post，导致其不会被发送
        return None

    def get_category(self, _) -> Category:
        return Category(1)

    async def parse(self, raw_post: BulletinListItem) -> Post:
        client = await self.ctx.get_client()
        raw_data = await client.get(f"https://ak-webview.hypergryph.com/api/game/bulletin/{self.get_id(post=raw_post)}")
        data = type_validate_python(ArkBulletinResponse, raw_data.json()).data

        def title_escape(text: str) -> str:
            return text.replace("\\n", " - ")

        # gen title, content
        if data.header:
            # header是title的更详细版本
            # header会和content一起出现
            title = data.header
        else:
            # 只有一张图片
            title = title_escape(data.title)

        return ArknightsPost(
            self,
            content=data.content,
            title=title,
            nickname="明日方舟游戏内公告",
            images=[data.banner_image_url] if data.banner_image_url else None,
            url=(url.human_repr() if (url := URL(data.jump_link)).scheme.startswith("http") else None),
            timestamp=data.updated_at,
            compress=True,
        )


class AkVersion(StatusChange):
    categories: ClassVar[dict[Category, str]] = {2: "更新信息"}
    platform_name = "arknights"
    name = "明日方舟游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    site = ArknightsSite
    has_target = False
    default_theme = "brief"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "明日方舟游戏信息"

    async def get_status(self, _):
        client = await self.ctx.get_client()
        res_ver = await client.get("https://ak-conf.hypergryph.com/config/prod/official/IOS/version")
        res_preanounce = await client.get(
            "https://ak-conf.hypergryph.com/config/prod/announce_meta/IOS/preannouncement.meta.json"
        )
        res = res_ver.json()
        res.update(res_preanounce.json())
        return res

    def compare_status(self, _, old_status, new_status):
        res = []
        ArkUpdatePost = partial(Post, self, "", nickname="明日方舟更新信息")
        if old_status.get("preAnnounceType") == 2 and new_status.get("preAnnounceType") == 0:
            res.append(ArkUpdatePost(title="登录界面维护公告上线（大概是开始维护了)"))
        elif old_status.get("preAnnounceType") == 0 and new_status.get("preAnnounceType") == 2:
            res.append(ArkUpdatePost(title="登录界面维护公告下线（大概是开服了，冲！）"))
        if old_status.get("clientVersion") != new_status.get("clientVersion"):
            res.append(ArkUpdatePost(title="游戏本体更新（大更新）"))
        if old_status.get("resVersion") != new_status.get("resVersion"):
            res.append(ArkUpdatePost(title="游戏资源更新（小更新）"))
        return res

    def get_category(self, _):
        return Category(2)

    async def parse(self, raw_post):
        return raw_post


class MonsterSiren(NewMessage):
    categories: ClassVar[dict[Category, str]] = {3: "塞壬唱片新闻"}
    platform_name = "arknights"
    name = "明日方舟游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    site = ArknightsSite
    has_target = False

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "明日方舟游戏信息"

    async def get_sub_list(self, _) -> list[RawPost]:
        client = await self.ctx.get_client()
        raw_data = await client.get("https://monster-siren.hypergryph.com/api/news")
        return raw_data.json()["data"]["list"]

    def get_id(self, post: RawPost) -> Any:
        return post["cid"]

    def get_date(self, _) -> None:
        return None

    def get_category(self, _) -> Category:
        return Category(3)

    async def parse(self, raw_post: RawPost) -> Post:
        client = await self.ctx.get_client()
        url = f"https://monster-siren.hypergryph.com/info/{raw_post['cid']}"
        res = await client.get(f"https://monster-siren.hypergryph.com/api/news/{raw_post['cid']}")
        raw_data = res.json()
        content = raw_data["data"]["content"]
        content = content.replace("</p>", "</p>\n")
        soup = bs(content, "html.parser")
        imgs = [x["src"] for x in soup("img")]
        text = f"{raw_post['title']}\n{soup.text.strip()}"
        return Post(
            self,
            content=text,
            images=imgs,
            url=url,
            nickname="塞壬唱片新闻",
            compress=True,
        )


class TerraHistoricusComic(NewMessage):
    categories: ClassVar[dict[Category, str]] = {4: "泰拉记事社漫画"}
    platform_name = "arknights"
    name = "明日方舟游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    site = ArknightsSite
    has_target = False
    default_theme = "brief"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "明日方舟游戏信息"

    async def get_sub_list(self, _) -> list[RawPost]:
        client = await self.ctx.get_client()
        raw_data = await client.get("https://terra-historicus.hypergryph.com/api/recentUpdate")
        return raw_data.json()["data"]

    def get_id(self, post: RawPost) -> Any:
        return f"{post['comicCid']}/{post['episodeCid']}"

    def get_date(self, _) -> None:
        return None

    def get_category(self, _) -> Category:
        return Category(4)

    async def parse(self, raw_post: RawPost) -> Post:
        url = f"https://terra-historicus.hypergryph.com/comic/{raw_post['comicCid']}/episode/{raw_post['episodeCid']}"
        return Post(
            self,
            content=raw_post["subtitle"],
            title=f"{raw_post['title']} - {raw_post['episodeShortTitle']}",
            images=[raw_post["coverUrl"]],
            url=url,
            nickname="泰拉记事社漫画",
            compress=True,
        )
