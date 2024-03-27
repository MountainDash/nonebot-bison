import re
import json
from abc import ABC
from copy import deepcopy
from enum import Enum, unique
from typing_extensions import Self
from datetime import datetime, timedelta
from typing import Any, TypeVar, TypeAlias, NamedTuple

from httpx import AsyncClient
from nonebot.log import logger
from pydantic import Field, BaseModel
from nonebot.compat import PYDANTIC_V2, ConfigDict, type_validate_json, type_validate_python

from nonebot_bison.compat import model_rebuild

from ..post import Post
from ..types import Tag, Target, RawPost, ApiError, Category
from ..utils import SchedulerConfig, http_client, text_similarity
from .platform import NewMessage, StatusChange, CategoryNotSupport, CategoryNotRecognize

TBaseModel = TypeVar("TBaseModel", bound=type[BaseModel])


# 不能当成装饰器用
# 当装饰器用时，global namespace 中还没有被装饰的类，会报错
def model_rebuild_recurse(cls: TBaseModel) -> TBaseModel:
    """Recursively rebuild all BaseModel subclasses in the class."""
    if not PYDANTIC_V2:
        from inspect import isclass, getmembers

        for _, sub_cls in getmembers(cls, lambda x: isclass(x) and issubclass(x, BaseModel)):
            model_rebuild_recurse(sub_cls)
    model_rebuild(cls)
    return cls


class Base(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:

        class Config:
            orm_mode = True


class APIBase(Base):
    """Bilibili API返回的基础数据"""

    code: int
    message: str


class UserAPI(APIBase):
    class Card(Base):
        name: str

    class Data(Base):
        card: "UserAPI.Card"

    data: Data | None = None


class PostAPI(APIBase):
    class Info(Base):
        uname: str

    class UserProfile(Base):
        info: "PostAPI.Info"

    class Origin(Base):
        uid: int
        dynamic_id: int
        dynamic_id_str: str
        timestamp: int
        type: int
        rid: int
        bvid: str | None = None

    class Desc(Base):
        dynamic_id: int
        dynamic_id_str: str
        timestamp: int
        type: int
        user_profile: "PostAPI.UserProfile"
        rid: int
        bvid: str | None = None

        origin: "PostAPI.Origin | None" = None

    class Card(Base):
        desc: "PostAPI.Desc"
        card: str

    class Data(Base):
        cards: "list[PostAPI.Card] | None"

    data: Data | None = None


DynRawPost: TypeAlias = PostAPI.Card

model_rebuild_recurse(UserAPI)
model_rebuild_recurse(PostAPI)


class BilibiliClient:
    _client: AsyncClient
    _refresh_time: datetime
    cookie_expire_time = timedelta(hours=5)

    def __init__(self) -> None:
        self._client = http_client()
        self._refresh_time = datetime(year=2000, month=1, day=1)  # an expired time

    async def _init_session(self):
        res = await self._client.get("https://www.bilibili.com/")
        if res.status_code != 200:
            logger.warning("unable to refresh temp cookie")
        else:
            self._refresh_time = datetime.now()

    async def _refresh_client(self):
        if datetime.now() - self._refresh_time > self.cookie_expire_time:
            await self._init_session()

    async def get_client(self) -> AsyncClient:
        await self._refresh_client()
        return self._client


bilibili_client = BilibiliClient()


class BaseSchedConf(ABC, SchedulerConfig):
    schedule_type = "interval"
    bilibili_client: BilibiliClient

    def __init__(self):
        super().__init__()
        self.bilibili_client = bilibili_client

    async def get_client(self, _: Target) -> AsyncClient:
        return await self.bilibili_client.get_client()

    async def get_query_name_client(self) -> AsyncClient:
        return await self.bilibili_client.get_client()


class BilibiliSchedConf(BaseSchedConf):
    name = "bilibili.com"
    schedule_setting = {"seconds": 10}


class BililiveSchedConf(BaseSchedConf):
    name = "live.bilibili.com"
    schedule_setting = {"seconds": 3}


class Bilibili(NewMessage):
    categories = {
        1: "一般动态",
        2: "专栏文章",
        3: "视频",
        4: "纯文字",
        5: "转发",
        # 5: "短视频"
    }
    platform_name = "bilibili"
    enable_tag = True
    enabled = True
    is_common = True
    scheduler = BilibiliSchedConf
    name = "B站"
    has_target = True
    parse_target_promot = "请输入用户主页的链接"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        res = await client.get("https://api.bilibili.com/x/web-interface/card", params={"mid": target})
        res.raise_for_status()
        res_data = type_validate_json(UserAPI, res.content)
        if res_data.code != 0:
            return None
        return res_data.data.card.name if res_data.data else None

    @classmethod
    async def parse_target(cls, target_text: str) -> Target:
        if re.match(r"\d+", target_text):
            return Target(target_text)
        elif m := re.match(r"(?:https?://)?space\.bilibili\.com/(\d+)", target_text):
            return Target(m.group(1))
        else:
            raise cls.ParseTargetException()

    async def get_sub_list(self, target: Target) -> list[DynRawPost]:
        params = {"host_uid": target, "offset": 0, "need_top": 0}
        res = await self.client.get(
            "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history",
            params=params,
            timeout=4.0,
        )
        res.raise_for_status()
        res_obj = type_validate_json(PostAPI, res.content)

        if res_obj.code == 0:
            if (data := res_obj.data) and (card := data.cards):
                return card
            return []
        raise ApiError(res.request.url)

    def get_id(self, post: DynRawPost) -> int:
        return post.desc.dynamic_id

    def get_date(self, post: DynRawPost) -> int:
        return post.desc.timestamp

    def _do_get_category(self, post_type: int) -> Category:
        match post_type:
            case 2:
                return Category(1)
            case 64:
                return Category(2)
            case 8:
                return Category(3)
            case 4:
                return Category(4)
            case 1:
                # 转发
                return Category(5)
            case unknown_type:
                raise CategoryNotRecognize(unknown_type)

    def get_category(self, post: DynRawPost) -> Category:
        post_type = post.desc.type
        return self._do_get_category(post_type)

    def get_tags(self, raw_post: DynRawPost) -> list[Tag]:
        card_content = json.loads(raw_post.card)
        text: str = card_content["item"]["content"]
        result: list[str] = re.findall(r"#(.*?)#", text)
        return result

    def _text_process(self, dynamic: str, desc: str, title: str) -> str:
        similarity = 1.0 if len(dynamic) == 0 or len(desc) == 0 else text_similarity(dynamic, desc)
        if len(dynamic) == 0 and len(desc) == 0:
            text = title
        elif similarity > 0.8:
            text = title + "\n\n" + desc if len(dynamic) < len(desc) else dynamic + "\n=================\n" + title
        else:
            text = dynamic + "\n=================\n" + title + "\n\n" + desc
        return text

    def _raw_post_parse(self, raw_post: DynRawPost, in_repost: bool = False):
        class ParsedPost(NamedTuple):
            text: str
            pics: list[str]
            url: str | None
            repost_owner: str | None = None
            repost: "ParsedPost | None" = None

        card_content: dict[str, Any] = json.loads(raw_post.card)
        repost_owner: str | None = ou["info"]["uname"] if (ou := card_content.get("origin_user")) else None

        def extract_url_id(url_template: str, name: str) -> str | None:
            if in_repost:
                if origin := raw_post.desc.origin:
                    return url_template.format(getattr(origin, name))
                return None
            return url_template.format(getattr(raw_post.desc, name))

        match self._do_get_category(raw_post.desc.type):
            case 1:
                # 一般动态
                url = extract_url_id("https://t.bilibili.com/{}", "dynamic_id_str")
                text: str = card_content["item"]["description"]
                pic: list[str] = [img["img_src"] for img in card_content["item"]["pictures"]]
                return ParsedPost(text, pic, url, repost_owner)
            case 2:
                # 专栏文章
                url = extract_url_id("https://www.bilibili.com/read/cv{}", "rid")
                text = "{} {}".format(card_content["title"], card_content["summary"])
                pic = card_content["image_urls"]
                return ParsedPost(text, pic, url, repost_owner)
            case 3:
                # 视频
                url = extract_url_id("https://www.bilibili.com/video/{}", "bvid")
                dynamic = card_content.get("dynamic", "")
                title = card_content["title"]
                desc = card_content.get("desc", "")
                text = self._text_process(dynamic, desc, title)
                pic = [card_content["pic"]]
                return ParsedPost(text, pic, url, repost_owner)
            case 4:
                # 纯文字
                url = extract_url_id("https://t.bilibili.com/{}", "dynamic_id_str")
                text = card_content["item"]["content"]
                pic = []
                return ParsedPost(text, pic, url, repost_owner)
            case 5:
                # 转发
                url = extract_url_id("https://t.bilibili.com/{}", "dynamic_id_str")
                text = card_content["item"]["content"]
                orig_type: int = card_content["item"]["orig_type"]
                orig_card: str = card_content["origin"]
                orig_post = DynRawPost(desc=raw_post.desc, card=orig_card)
                orig_post.desc.type = orig_type

                orig_parsed_post = self._raw_post_parse(orig_post, in_repost=True)
                return ParsedPost(text, [], url, repost_owner, orig_parsed_post)
            case unsupported_type:
                raise CategoryNotSupport(unsupported_type)

    async def parse(self, raw_post: DynRawPost) -> Post:
        parsed_raw_post = self._raw_post_parse(raw_post)

        post = Post(
            self,
            parsed_raw_post.text,
            url=parsed_raw_post.url,
            images=list(parsed_raw_post.pics),
            nickname=raw_post.desc.user_profile.info.uname,
        )
        if rp := parsed_raw_post.repost:
            post.repost = Post(
                self,
                rp.text,
                url=rp.url,
                images=list(rp.pics),
                nickname=rp.repost_owner,
            )
        return post


class Bilibililive(StatusChange):
    categories = {1: "开播提醒", 2: "标题更新提醒", 3: "下播提醒"}
    platform_name = "bilibili-live"
    enable_tag = False
    enabled = True
    is_common = True
    scheduler = BililiveSchedConf
    name = "Bilibili直播"
    has_target = True
    use_batch = True
    default_theme = "brief"

    @unique
    class LiveStatus(Enum):
        # 直播状态
        # 0: 未开播
        # 1: 正在直播
        # 2: 轮播中
        OFF = 0
        ON = 1
        CYCLE = 2

    @unique
    class LiveAction(Enum):
        # 当前直播行为，由新旧直播状态对比决定
        # on: 正在直播
        # off: 未开播
        # turn_on: 状态变更为正在直播
        # turn_off: 状态变更为未开播
        # title_update: 标题更新
        TURN_ON = "turn_on"
        TURN_OFF = "turn_off"
        ON = "on"
        OFF = "off"
        TITLE_UPDATE = "title_update"

    class Info(BaseModel):
        title: str
        room_id: int  # 直播间号
        uid: int  # 主播uid
        live_time: int  # 开播时间
        live_status: "Bilibililive.LiveStatus"
        area_name: str = Field(alias="area_v2_name")  # 新版分区名
        uname: str  # 主播名
        face: str  # 头像url
        cover: str = Field(alias="cover_from_user")  # 封面url
        keyframe: str  # 关键帧url，可能会有延迟
        category: Category = Field(default=Category(0))

        def get_live_action(self, old_info: Self) -> "Bilibililive.LiveAction":
            status = Bilibililive.LiveStatus
            action = Bilibililive.LiveAction
            if old_info.live_status in [status.OFF, status.CYCLE] and self.live_status == status.ON:
                return action.TURN_ON
            elif old_info.live_status == status.ON and self.live_status in [
                status.OFF,
                status.CYCLE,
            ]:
                return action.TURN_OFF
            elif old_info.live_status == status.ON and self.live_status == status.ON:
                if old_info.title != self.title:
                    # 开播时通常会改标题，避免短时间推送两次
                    return action.TITLE_UPDATE
                else:
                    return action.ON
            else:
                return action.OFF

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        res = await client.get("https://api.bilibili.com/x/web-interface/card", params={"mid": target})
        res_data = json.loads(res.text)
        if res_data["code"]:
            return None
        return res_data["data"]["card"]["name"]

    def _gen_empty_info(self, uid: int) -> Info:
        """返回一个空的Info，用于该用户没有直播间的情况"""
        return Bilibililive.Info(
            title="",
            room_id=0,
            uid=uid,
            live_time=0,
            live_status=Bilibililive.LiveStatus.OFF,
            area_v2_name="",
            uname="",
            face="",
            cover_from_user="",
            keyframe="",
        )

    async def batch_get_status(self, targets: list[Target]) -> list[Info]:
        # https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/live/info.md#批量查询直播间状态
        res = await self.client.get(
            "https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids",
            params={"uids[]": targets},
            timeout=4.0,
        )
        res_dict = res.json()

        if res_dict["code"] != 0:
            raise self.FetchError()

        data = res_dict.get("data", {})
        infos = []
        for target in targets:
            if target in data.keys():
                infos.append(type_validate_python(self.Info, data[target]))
            else:
                infos.append(self._gen_empty_info(int(target)))
        return infos

    def compare_status(self, _: Target, old_status: Info, new_status: Info) -> list[RawPost]:
        action = Bilibililive.LiveAction
        match new_status.get_live_action(old_status):
            case action.TURN_ON:
                return self._gen_current_status(new_status, 1)
            case action.TITLE_UPDATE:
                return self._gen_current_status(new_status, 2)
            case action.TURN_OFF:
                return self._gen_current_status(new_status, 3)
            case _:
                return []

    def _gen_current_status(self, new_status: Info, category: Category):
        current_status = deepcopy(new_status)
        current_status.category = Category(category)
        return [current_status]

    def get_category(self, status: Info) -> Category:
        assert status.category != Category(0)
        return status.category

    async def parse(self, raw_post: Info) -> Post:
        url = f"https://live.bilibili.com/{raw_post.room_id}"
        pic = [raw_post.cover] if raw_post.category == Category(1) else [raw_post.keyframe]
        title = f"[{self.categories[raw_post.category].rstrip('提醒')}] {raw_post.title}"
        target_name = f"{raw_post.uname} {raw_post.area_name}"
        return Post(
            self,
            "",
            title=title,
            url=url,
            images=list(pic),
            nickname=target_name,
            compress=True,
        )


class BilibiliBangumi(StatusChange):
    categories = {}
    platform_name = "bilibili-bangumi"
    enable_tag = False
    enabled = True
    is_common = True
    scheduler = BilibiliSchedConf
    name = "Bilibili剧集"
    has_target = True
    parse_target_promot = "请输入剧集主页"
    default_theme = "brief"

    _url = "https://api.bilibili.com/pgc/review/user"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        res = await client.get(cls._url, params={"media_id": target})
        res_data = res.json()
        if res_data["code"]:
            return None
        return res_data["result"]["media"]["title"]

    @classmethod
    async def parse_target(cls, target_string: str) -> Target:
        if re.match(r"\d+", target_string):
            return Target(target_string)
        elif m := re.match(r"md(\d+)", target_string):
            return Target(m[1])
        elif m := re.match(r"(?:https?://)?www\.bilibili\.com/bangumi/media/md(\d+)", target_string):
            return Target(m[1])
        raise cls.ParseTargetException()

    async def get_status(self, target: Target):
        res = await self.client.get(
            self._url,
            params={"media_id": target},
            timeout=4.0,
        )
        res_dict = res.json()
        if res_dict["code"] == 0:
            return {
                "index": res_dict["result"]["media"]["new_ep"]["index"],
                "index_show": res_dict["result"]["media"]["new_ep"]["index_show"],
                "season_id": res_dict["result"]["media"]["season_id"],
            }
        else:
            raise self.FetchError

    def compare_status(self, target: Target, old_status, new_status) -> list[RawPost]:
        if new_status["index"] != old_status["index"]:
            return [new_status]
        else:
            return []

    async def parse(self, raw_post: RawPost) -> Post:
        detail_res = await self.client.get(
            f'https://api.bilibili.com/pgc/view/web/season?season_id={raw_post["season_id"]}'
        )
        detail_dict = detail_res.json()
        lastest_episode = None
        for episode in detail_dict["result"]["episodes"][::-1]:
            if episode["badge"] in ("", "会员"):
                lastest_episode = episode
                break
        if not lastest_episode:
            lastest_episode = detail_dict["result"]["episodes"]

        url = lastest_episode["link"]
        pic: list[str] = [lastest_episode["cover"]]
        target_name = detail_dict["result"]["season_title"]
        content = raw_post["index_show"]
        title = lastest_episode["share_copy"]
        return Post(
            self,
            content,
            title=title,
            url=url,
            images=list(pic),
            nickname=target_name,
            compress=True,
        )


model_rebuild(Bilibililive.Info)
