from functools import partial
from typing import Any, ClassVar

from httpx import AsyncClient
from nonebot.compat import type_validate_python
from pydantic import BaseModel, Field

from nonebot_bison.post import Post
from nonebot_bison.types import Category, Target

from .arknights import HGAnnouncePost, HypergryphSite
from .platform import NewMessage, RawPost, StatusChange


class EFResponseBase(BaseModel):
    code: int
    msg: str


class BulletinOnlineItem(BaseModel):
    cid: str
    version: int
    need_red_dot: bool = Field(alias="needRedDot")
    need_popup: bool = Field(alias="needPopup")


class BulletinListItem(BaseModel):
    cid: str
    title: str
    type: int
    tab: str
    order_type: int = Field(alias="orderType")
    order_weight: int = Field(alias="orderWeight")
    display_type: str = Field(alias="displayType")
    start_at: int = Field(alias="startAt")
    focus: int


class BulletinList(BaseModel):
    topic_cid: str = Field(alias="topicCid")
    type: int
    platform: str
    server: str
    channel: str
    sub_channel: str = Field(alias="subChannel")
    lang: str
    key: str
    version: str
    online_list: list[BulletinOnlineItem] = Field(alias="onlineList")
    popup_version: int = Field(alias="popupVersion")
    updated_at: int = Field(alias="updatedAt")
    list: list[BulletinListItem]


class BulletinPayload(BaseModel):
    html: str | None = None
    url: str | None = None
    link: str | None = None
    link_type: int | None = Field(default=None, alias="linkType")


class BulletinData(BaseModel):
    cid: str
    type: int
    tab: str
    order_type: int = Field(alias="orderType")
    order_weight: int = Field(alias="orderWeight")
    display_type: str = Field(alias="displayType")
    focus: int
    start_at: int = Field(alias="startAt")
    title: str
    header: str | None = None
    jump_button: Any | None = Field(default=None, alias="jumpButton")
    data: BulletinPayload
    need_red_dot: bool = Field(alias="needRedDot")
    need_popup: bool = Field(alias="needPopup")
    version: int


class CleanedBulletinData(BaseModel):
    title: str
    content: str = ""
    images: list[str] | None = None
    link: str = ""


def title_escape(text: str) -> str:
    return text.replace("\\n", " - ")


def clean_bulletin(data: BulletinData) -> CleanedBulletinData:
    title = title_escape(data.header if data.header else data.title)

    payload = data.data
    if data.display_type == "picture":
        content = ""
        images = [payload.url] if payload.url else None
        link = payload.link if payload.link else ""
    elif data.display_type == "rich_text":
        content = payload.html if payload.html else ""
        images = None
        link = ""
    else:
        content = payload.html if payload.html else ""
        images = None
        link = payload.link if payload.link else ""
    return CleanedBulletinData(title=title, content=content, images=images, link=link)


class EFBulletinListResponse(EFResponseBase):
    data: BulletinList


class EFBulletinResponse(EFResponseBase):
    data: BulletinData


class Endfield(NewMessage):
    categories: ClassVar[dict[Category, str]] = {1: "游戏公告"}
    platform_name = "endfield"
    name = "终末地游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    site = HypergryphSite
    has_target = False
    default_theme = "arknights"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "终末地游戏信息"

    async def get_sub_list(self, _) -> list[BulletinListItem]:
        client = await self.ctx.get_client()
        raw_data = await client.get(
            "https://game-hub.hypergryph.com/bulletin/v2/aggregate?lang=zh-cn&platform=Windows&channel=1&subChannel=1&type=0&code=endfield_5SD9TN&hideDetail=1"
        )
        return type_validate_python(EFBulletinListResponse, raw_data.json()).data.list

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
        raw_url = f"https://game-hub.hypergryph.com/bulletin/detail/{self.get_id(post=raw_post)}?lang=zh-cn&code=endfield_5SD9TN"
        raw_data = await client.get(raw_url)
        data = type_validate_python(EFBulletinResponse, raw_data.json()).data

        cleaned_data = clean_bulletin(data)

        return HGAnnouncePost(
            self,
            content=cleaned_data.content,
            title=cleaned_data.title,
            nickname="终末地游戏内公告",
            images=cleaned_data.images,
            url=cleaned_data.link,
            timestamp=data.start_at,
            compress=True,
        )


class Endfield2(NewMessage):
    categories: ClassVar[dict[Category, str]] = {2: "游戏公告（登陆页面版）"}
    platform_name = "endfield"
    name = "终末地游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    site = HypergryphSite
    has_target = False
    default_theme = "arknights"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "终末地游戏信息"

    async def get_sub_list(self, _) -> list[BulletinListItem]:
        client = await self.ctx.get_client()
        raw_data = await client.get(
            "https://game-hub.hypergryph.com/bulletin/v2/aggregate?lang=zh-cn&platform=Windows&channel=1&subChannel=1&type=1&code=endfield_5SD9TN&hideDetail=1"
        )
        return type_validate_python(EFBulletinListResponse, raw_data.json()).data.list

    def get_id(self, post: BulletinListItem) -> Any:
        return post.cid

    def get_date(self, post: BulletinListItem) -> Any:
        # 为什么不使用post.updated_at？
        # update_at的时间是上传鹰角服务器的时间，而不是公告发布的时间
        # 也就是说鹰角可能会在中午就把晚上的公告上传到服务器，但晚上公告才会显示，但是update_at就是中午的时间不会改变
        # 如果指定了get_date，那么get_date会被优先使用, 并在获取到的值超过2小时时忽略这条post，导致其不会被发送
        return None

    def get_category(self, _) -> Category:
        return Category(2)

    async def parse(self, raw_post: BulletinListItem) -> Post:
        client = await self.ctx.get_client()
        raw_url = f"https://game-hub.hypergryph.com/bulletin/detail/{self.get_id(post=raw_post)}?lang=zh-cn&code=endfield_5SD9TN"
        raw_data = await client.get(raw_url)
        data = type_validate_python(EFBulletinResponse, raw_data.json()).data

        cleaned_data = clean_bulletin(data)

        return HGAnnouncePost(
            self,
            content=cleaned_data.content,
            title=cleaned_data.title,
            nickname="终末地游戏登陆页面公告",
            images=cleaned_data.images,
            url=cleaned_data.link,
            timestamp=data.start_at,
            compress=True,
        )


class EFVersion(StatusChange):
    categories: ClassVar[dict[Category, str]] = {3: "更新信息"}
    platform_name = "endfield"
    name = "终末地游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    site = HypergryphSite
    has_target = False
    default_theme = "brief"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "终末地游戏信息"

    async def get_status(self, _):
        client = await self.ctx.get_client()
        version = await client.get(
            "https://launcher.hypergryph.com/api/game/get_latest?appcode=6LL0KJuqHBVz33WK&channel=1&platform=Windows&sub_channel=1&source=game"
        )
        return version.json().get("version", "")

    def compare_status(self, _, old_status, new_status):
        res = []
        EFUpdatePost = partial(Post, self, "", nickname="终末地更新信息")
        if old_status != new_status:
            res.append(EFUpdatePost(title=f"终末地版本更新：{old_status} -> {new_status}"))
        return res

    def get_category(self, _):
        return Category(3)

    async def parse(self, raw_post):
        return raw_post


class TerraHistoricusComic(NewMessage):
    categories: ClassVar[dict[Category, str]] = {4: "塔卫二记事社漫画"}
    platform_name = "endfield"
    name = "终末地游戏信息"
    enable_tag = False
    enabled = True
    is_common = False
    site = HypergryphSite
    has_target = False
    default_theme = "brief"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "终末地游戏信息"

    async def get_sub_list(self, _) -> list[RawPost]:
        client = await self.ctx.get_client()
        raw_data = await client.get("https://comic.hypergryph.com/api/recentUpdate?topicKey=talos-ii-historicus")
        return raw_data.json()["data"]

    def get_id(self, post: RawPost) -> Any:
        return f"{post['comicCid']}/{post['episodeCid']}"

    def get_date(self, _) -> None:
        return None

    def get_category(self, _) -> Category:
        return Category(4)

    async def parse(self, raw_post: RawPost) -> Post:
        url = f"https://comic.hypergryph.com/talos-ii-historicus/comic/{raw_post['comicCid']}/episode/{raw_post['episodeCid']}"
        return Post(
            self,
            content=raw_post["subtitle"],
            title=f"{raw_post['title']} - {raw_post['episodeShortTitle']}",
            images=[raw_post["coverUrl"]],
            url=url,
            nickname="塔卫二记事社漫画",
            compress=True,
        )
