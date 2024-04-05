import re
import json
from copy import deepcopy
from random import randint
from enum import Enum, unique
from typing_extensions import Self
from datetime import datetime, timedelta
from typing import Any, Literal, TypeVar, TypeAlias, NamedTuple

from yarl import URL
from httpx import AsyncClient
from nonebot import logger, require
from pydantic import Field, BaseModel
from nonebot.compat import PYDANTIC_V2, ConfigDict, type_validate_json, type_validate_python

from ..post import Post
from ..compat import model_rebuild
from ..types import Tag, Target, RawPost, ApiError, Category
from ..utils import Site, ClientManager, http_client, text_similarity
from .platform import NewMessage, StatusChange, CategoryNotSupport, CategoryNotRecognize

require("nonebot_plugin_htmlrender")
from playwright.async_api import Page, Cookie
from nonebot_plugin_htmlrender import get_browser

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


DynamicType = Literal[
    "DYNAMIC_TYPE_ARTICLE",
    "DYNAMIC_TYPE_AV",
    "DYNAMIC_TYPE_WORD",
    "DYNAMIC_TYPE_DRAW",
    "DYNAMIC_TYPE_FORWARD",
    "DYNAMIC_TYPE_LIVE",
    "DYNAMIC_TYPE_LIVE_RCMD",
    "DYNAMIC_TYPE_PGC",
    "DYNAMIC_TYPE_PGC_UNION",
    "DYNAMIC_TYPE_NONE",  # 已删除的动态，一般只会出现在转发动态的源动态被删除
    "DYNAMIC_TYPE_COMMON_SQUARE",
    "DYNAMIC_TYPE_COMMON_VERTICAL",
    "DYNAMIC_TYPE_COURSES_SEASON",
]


# 参考 https://github.com/Yun-Shan/bilibili-dynamic
class PostAPI(APIBase):
    class Basic(Base):
        rid_str: str
        """可能含义是referrer id，表示引用的对象的ID？
        已知专栏动态时该ID与专栏ID一致，视频动态时与av号一致
        """

    class Modules(Base):
        class Author(Base):
            face: str
            mid: int
            name: str
            jump_url: str
            pub_ts: int
            type: Literal["AUTHOR_TYPE_NORMAL", "AUTHOR_TYPE_PGC"]
            """作者类型，一般情况下都是NORMAL，番剧推送是PGC"""

        class Additional(Base):
            type: str
            """用户发视频时同步发布的动态带图片: ADDITIONAL_TYPE_UGC
            显示相关游戏: ADDITIONAL_TYPE_COMMON
            显示预约: ADDITIONAL_TYPE_RESERVE
            显示投票: ADDITIONAL_TYPE_VOTE
            显示包月充电专属抽奖: ADDITIONAL_TYPE_UPOWER_LOTTERY
            显示赛事时(暂时只看到回放的，理论上直播时应该也是这个): ADDITIONAL_TYPE_MATCH
            """

        class Desc(Base):
            rich_text_nodes: list[dict[str, Any]]
            """描述的富文本节点，组成动态的各种内容"""
            text: str
            """描述的纯文本内容"""

        class Dynamic(Base):
            additional: "PostAPI.Modules.Additional"
            desc: "PostAPI.Modules.Desc | None" = None
            """动态描述，可能为空"""
            major: "Major | UnknownMajor | None" = None
            """主要内容，可能为空"""

        module_author: "PostAPI.Modules.Author"
        module_dynamic: "PostAPI.Modules.Dynamic"

    class Topic(Base):
        id: int
        name: str
        jump_url: str

    class Item(Base):
        basic: "PostAPI.Basic"
        id_str: str
        modules: "PostAPI.Modules"
        orig: "PostAPI.Item | None" = None
        topic: "PostAPI.Topic | None" = None
        type: DynamicType

    class Data(Base):
        items: "list[PostAPI.Item] | None" = None

    data: "PostAPI.Data | None" = None


class VideoMajor(Base):
    class Archive(Base):
        aid: str
        bvid: str
        title: str
        desc: str
        """视频简介，太长的话会被截断"""
        cover: str
        jump_url: str

    type: Literal["MAJOR_TYPE_ARCHIVE"]
    archive: "VideoMajor.Archive"


class LiveRecommendMajor(Base):
    class LiveRecommand(Base):
        content: str
        """直播卡片的内容，值为JSON文本"""

    type: Literal["MAJOR_TYPE_LIVE_RCMD"]
    live_rcmd: "LiveRecommendMajor.LiveRecommand"


class LiveMajor(Base):
    class Live(Base):
        id: int
        """直播间号"""
        title: str
        live_state: int
        """直播状态，1为直播中，0为未开播"""
        cover: str
        desc_first: str
        """直播信息的第一部分，用来显示分区"""
        desc_second: str
        """跳转链接，目前用的是相对协议(即//开头而不是https://开头)"""
        jump_url: str

    type: Literal["MAJOR_TYPE_LIVE"]
    live: "LiveMajor.Live"


class ArticleMajor(Base):
    class Article(Base):
        id: int
        """专栏CID"""
        title: str
        desc: str
        """专栏简介"""
        covers: list[str]
        """专栏封面，一般是一张图片"""
        jump_url: str

    type: Literal["MAJOR_TYPE_ARTICLE"]
    article: "ArticleMajor.Article"


class DrawMajor(Base):
    class Item(Base):
        width: int
        height: int
        size: int
        """文件大小，KiB（1024）"""
        src: str
        """图片链接"""

    class Draw(Base):
        id: int
        items: "list[DrawMajor.Item]"

    type: Literal["MAJOR_TYPE_DRAW"]
    draw: "DrawMajor.Draw"


class PGCMajor(Base):
    """番剧推送"""

    class PGC(Base):
        title: str
        cover: str
        jump_url: str
        """通常https://www.bilibili.com/bangumi/play/ep{epid}"""
        epid: int
        season_id: int

    type: Literal["MAJOR_TYPE_PGC"]
    pgc: "PGCMajor.PGC"


class OPUSMajor(Base):
    """通用图文内容"""

    class Summary(Base):
        rich_text_nodes: list[dict[str, Any]]
        """描述的富文本节点，组成动态的各种内容"""
        text: str

    class Pic(Base):
        width: int
        height: int
        size: int
        """文件大小，KiB（1024）"""
        url: str
        """图片链接"""

    class Opus(Base):
        jump_url: str
        title: str
        summary: "OPUSMajor.Summary"
        pics: "list[OPUSMajor.Pic]"

    type: Literal["MAJOR_TYPE_OPUS"]
    opus: "OPUSMajor.Opus"


class CommonMajor(Base):
    """还是通用图文内容
    主要跟特殊官方功能有关系，例如专属活动页、会员购、漫画、赛事中心、游戏中心、小黑屋、工房集市、装扮等
    """

    class Common(Base):
        cover: str
        """卡片左侧图片的URL"""
        title: str
        desc: str
        """内容"""
        jump_url: str

    type: Literal["MAJOR_TYPE_COMMON"]
    common: "CommonMajor.Common"


class CoursesMajor(Base):
    """课程推送"""

    class Courses(Base):
        title: str
        sub_title: str
        """副标题，一般是课程的简介"""
        desc: str
        """课时信息"""
        cover: str
        jump_url: str
        id: int
        """课程ID"""

    type: Literal["MAJOR_TYPE_COURSES"]
    courses: "CoursesMajor.Courses"


class UnknownMajor(Base):
    type: str


Major = (
    VideoMajor
    | LiveRecommendMajor
    | LiveMajor
    | ArticleMajor
    | DrawMajor
    | PGCMajor
    | OPUSMajor
    | CommonMajor
    | CoursesMajor
)

DynRawPost: TypeAlias = PostAPI.Item

model_rebuild_recurse(VideoMajor)
model_rebuild_recurse(LiveRecommendMajor)
model_rebuild_recurse(LiveMajor)
model_rebuild_recurse(ArticleMajor)
model_rebuild_recurse(DrawMajor)
model_rebuild_recurse(PGCMajor)
model_rebuild_recurse(OPUSMajor)
model_rebuild_recurse(CommonMajor)
model_rebuild_recurse(CoursesMajor)
model_rebuild_recurse(UserAPI)
model_rebuild_recurse(PostAPI)


class BilibiliClient(ClientManager):
    _client: AsyncClient
    _refresh_time: datetime
    _pw_page: Page | None = None
    _cookies: list[Cookie] = []
    cookie_expire_time = timedelta(hours=1)

    def __init__(self) -> None:
        self._client = http_client()
        self._refresh_time = datetime(year=2000, month=1, day=1)  # an expired time

    async def _refresh_cookies(self, page: Page):
        await page.context.clear_cookies()
        await page.reload()
        await page.goto(f"https://space.bilibili.com/{randint(1, 1000)}/dynamic")
        self._cookies = await page.context.cookies()

        for cookie in self._cookies:
            self._client.cookies.set(
                name=cookie.get("name", ""),
                value=cookie.get("value", ""),
                domain=cookie.get("domain", ""),
                path=cookie.get("path", ""),
            )
        self._refresh_time = datetime.now()
        logger.debug("刷新B站客户端cookies完毕")

    async def _init_session(self):
        browser = await get_browser()
        self._pw_page = await browser.new_page()
        logger.debug("初始化B站客户端完毕")

    async def refresh_client(self, force: bool = False):
        logger.debug("尝试刷新B站客户端")
        if not self._pw_page:
            logger.debug("无打开页面，初始化B站客户端")
            await self._init_session()
        assert self._pw_page

        if force:
            await self._pw_page.close()
            await self._init_session()
            await self._refresh_cookies(self._pw_page)
            logger.debug("强制刷新B站客户端完毕")
        elif datetime.now() - self._refresh_time > self.cookie_expire_time:
            await self._pw_page.reload()
            await self._refresh_cookies(self._pw_page)
            logger.debug("刷新B站客户端完毕")

    async def get_client(self, target: Target | None) -> AsyncClient:
        await self._refresh_client()
        return self._client

    async def get_query_name_client(self) -> AsyncClient:
        await self._refresh_client()
        return self._client


class BilibiliSite(Site):
    name = "bilibili.com"
    schedule_type = "interval"
    schedule_setting = {"seconds": 10}
    client_mgr = BilibiliClient


class BililiveSchedConf(Site):
    name = "live.bilibili.com"
    schedule_type = "interval"
    schedule_setting = {"seconds": 3}
    client_mgr = BilibiliClient


class Bilibili(NewMessage):
    categories = {
        1: "一般动态",
        2: "专栏文章",
        3: "视频",
        4: "纯文字",
        5: "转发",
        6: "直播推送",
        # 5: "短视频"
    }
    platform_name = "bilibili"
    enable_tag = True
    enabled = True
    is_common = True
    site = BilibiliSite
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
        elif re.match(r"UID:\d+", target_text):
            return Target(target_text[4:])
        elif m := re.match(r"(?:https?://)?space\.bilibili\.com/(\d+)", target_text):
            return Target(m.group(1))
        else:
            raise cls.ParseTargetException(
                prompt="正确格式:\n1. 用户纯数字id\n2. UID:<用户id>\n3. 用户主页链接: https://space.bilibili.com/xxxx"
            )

    async def get_sub_list(self, target: Target) -> list[DynRawPost]:
        client = await self.ctx.get_client()
        params = {"host_uid": target, "offset": 0, "need_top": 0}
        res = await client.get(
            "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history",
            params=params,
            timeout=4.0,
        )
        res.raise_for_status()
        res_obj = type_validate_json(PostAPI, res.content)

        # 0: 成功
        # -352: 需要cookie
        if res_obj.code == 0:
            if (data := res_obj.data) and (items := data.items):
                logger.debug(f"获取用户{target}的动态列表成功，共{len(items)}条动态")
                logger.debug(f"用户{target}的动态列表: {':'.join(x.id_str for x in items)}")
                return items
            logger.debug(f"获取用户{target}的动态列表成功，但是没有动态")
            return []
        elif res_obj.code == -352:
            await bilibili_client.refresh_client(force=True)
        raise ApiError(res.request.url)

    def get_id(self, post: DynRawPost) -> str:
        return post.id_str

    def get_date(self, post: DynRawPost) -> int:
        return post.modules.module_author.pub_ts

    def _do_get_category(self, post_type: DynamicType) -> Category:
        match post_type:
            case "DYNAMIC_TYPE_DRAW" | "DYNAMIC_TYPE_COMMON_VERTICAL" | "DYNAMIC_TYPE_COMMON_SQUARE":
                return Category(1)
            case "DYNAMIC_TYPE_ARTICLE":
                return Category(2)
            case "DYNAMIC_TYPE_AV":
                return Category(3)
            case "DYNAMIC_TYPE_WORD":
                return Category(4)
            case "DYNAMIC_TYPE_FORWARD":
                # 转发
                return Category(5)
            case "DYNAMIC_TYPE_LIVE_RCMD" | "DYNAMIC_TYPE_LIVE":
                return Category(6)
            case unknown_type:
                raise CategoryNotRecognize(unknown_type)

    def get_category(self, post: DynRawPost) -> Category:
        post_type = post.type
        return self._do_get_category(post_type)

    def get_tags(self, raw_post: DynRawPost) -> list[Tag]:
        tags: list[Tag] = []
        if raw_post.topic:
            tags.append(raw_post.topic.name)
        if desc := raw_post.modules.module_dynamic.desc:
            # {
            #    "jump_url": "//search.bilibili.com/all?keyword=鸣潮公测定档",
            #    "orig_text": "#鸣潮公测定档#",
            #    "text": "#鸣潮公测定档#",
            #    "type": "RICH_TEXT_NODE_TYPE_TOPIC"
            # }
            for node in desc.rich_text_nodes:
                if (node_type := node.get("type", None)) and node_type == "RICH_TEXT_NODE_TYPE_TOPIC":
                    tags.append(node["text"].strip("#"))
        return tags

    def _text_process(self, dynamic: str, desc: str, title: str):
        class _ProcessedText(NamedTuple):
            title: str
            content: str

        # 计算视频标题和视频描述相似度
        title_similarity = 0.0 if len(title) == 0 or len(desc) == 0 else text_similarity(title, desc[: len(title)])
        if title_similarity > 0.9:
            desc = desc[len(title) :]
        # 计算视频描述和动态描述相似度
        content_similarity = 0.0 if len(dynamic) == 0 or len(desc) == 0 else text_similarity(dynamic, desc)
        if content_similarity > 0.8:
            return _ProcessedText(title, dynamic if len(dynamic) < len(desc) else desc)
        else:
            return _ProcessedText(title, f"{desc}\n=================\n{dynamic}")

    def _major_parser(self, raw_post: DynRawPost):
        class ParsedPost(NamedTuple):
            title: str
            content: str
            pics: list[str]
            url: str | None = None

        def make_common_dynamic_url() -> str:
            return f"https://t.bilibili.com/{raw_post.id_str}"

        def get_desc_text() -> str:
            dyn = raw_post.modules.module_dynamic
            return dyn.desc.text if dyn.desc else ""

        match raw_post.modules.module_dynamic.major:
            case VideoMajor(archive=archive):
                desc_text = get_desc_text()
                parsed = self._text_process(desc_text, archive.desc, archive.title)
                return ParsedPost(
                    title=parsed.title,
                    content=parsed.content,
                    pics=[archive.cover],
                    url=URL(archive.jump_url).with_scheme("https").human_repr(),
                )
            case LiveRecommendMajor(live_rcmd=live_rcmd):
                return ParsedPost(
                    title=get_desc_text(),
                    content=live_rcmd.content,
                    pics=[],
                    url=make_common_dynamic_url(),
                )
            case LiveMajor(live=live):
                return ParsedPost(
                    title=live.title,
                    content=f"{live.desc_first}\n{live.desc_second}",
                    pics=[live.cover],
                    url=URL(live.jump_url).with_scheme("https").human_repr(),
                )
            case ArticleMajor(article=article):
                return ParsedPost(
                    title=article.title,
                    content=article.desc,
                    pics=article.covers,
                    url=URL(article.jump_url).with_scheme("https").human_repr(),
                )
            case DrawMajor(draw=draw):
                return ParsedPost(
                    title="",
                    content=get_desc_text(),
                    pics=[item.src for item in draw.items],
                    url=make_common_dynamic_url(),
                )
            case PGCMajor(pgc=pgc):
                return ParsedPost(
                    title=pgc.title,
                    content="",
                    pics=[pgc.cover],
                    url=URL(pgc.jump_url).with_scheme("https").human_repr(),
                )
            case OPUSMajor(opus=opus):
                return ParsedPost(
                    title=opus.title,
                    content=opus.summary.text,
                    pics=[pic.url for pic in opus.pics],
                    url=URL(opus.jump_url).with_scheme("https").human_repr(),
                )
            case CommonMajor(common=common):
                return ParsedPost(
                    title=common.title,
                    content=common.desc,
                    pics=[common.cover],
                    url=URL(common.jump_url).with_scheme("https").human_repr(),
                )
            case CoursesMajor(courses=courses):
                return ParsedPost(
                    title=courses.title,
                    content=f"{courses.sub_title}\n{courses.desc}",
                    pics=[courses.cover],
                    url=URL(courses.jump_url).with_scheme("https").human_repr(),
                )
            case UnknownMajor(type=unknown_type):
                raise CategoryNotSupport(unknown_type)
            case _:
                raise CategoryNotSupport(f"{raw_post.id_str=}")

    async def parse(self, raw_post: DynRawPost) -> Post:
        parsed_raw_post = self._major_parser(raw_post)
        if self._do_get_category(raw_post.type) == Category(5):
            if raw_post.orig:
                parsed_raw_repost = self._major_parser(raw_post.orig)
            else:
                logger.warning(f"转发动态{raw_post.id_str}没有原动态")
                parsed_raw_repost = None

        post = Post(
            self,
            content=parsed_raw_post.content,
            title=parsed_raw_post.title,
            images=list(parsed_raw_post.pics),
            timestamp=self.get_date(raw_post),
            url=parsed_raw_post.url,
            avatar=raw_post.modules.module_author.face,
            nickname=raw_post.modules.module_author.name,
        )
        if parsed_raw_repost:
            orig = raw_post.orig
            assert orig
            post.repost = Post(
                self,
                content=parsed_raw_repost.content,
                title=parsed_raw_repost.title,
                images=list(parsed_raw_repost.pics),
                timestamp=self.get_date(orig),
                url=parsed_raw_repost.url,
                avatar=orig.modules.module_author.face,
                nickname=orig.modules.module_author.name,
            )
        return post


class Bilibililive(StatusChange):
    categories = {1: "开播提醒", 2: "标题更新提醒", 3: "下播提醒"}
    platform_name = "bilibili-live"
    enable_tag = False
    enabled = True
    is_common = True
    site = BililiveSchedConf
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
        client = await self.ctx.get_client()
        # https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/live/info.md#批量查询直播间状态
        res = await client.get(
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
    site = BilibiliSite
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
        raise cls.ParseTargetException(
            prompt="正确格式:\n1. 剧集id\n2. 剧集主页链接 https://www.bilibili.com/bangumi/media/mdxxxx"
        )

    async def get_status(self, target: Target):
        client = await self.ctx.get_client()
        res = await client.get(
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
        client = await self.ctx.get_client()
        detail_res = await client.get(f'https://api.bilibili.com/pgc/view/web/season?season_id={raw_post["season_id"]}')
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
