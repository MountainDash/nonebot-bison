from copy import deepcopy
from enum import Enum, unique
import re
from typing import ClassVar, NamedTuple
from typing_extensions import Self

from httpx import AsyncClient
from nonebot import logger
from nonebot.compat import type_validate_json, type_validate_python
from pydantic import BaseModel, Field, ValidationError
from yarl import URL

from nonebot_bison.compat import model_rebuild
from nonebot_bison.platform.platform import CategoryNotRecognize, CategoryNotSupport, NewMessage, StatusChange
from nonebot_bison.post.post import Post
from nonebot_bison.types import ApiError, Category, RawPost, Tag, Target
from nonebot_bison.utils import decode_unicode_escapes, text_similarity

from .models import (
    ArticleMajor,
    CommonMajor,
    CoursesMajor,
    DeletedMajor,
    DrawMajor,
    DynamicType,
    DynRawPost,
    LiveMajor,
    LiveRecommendMajor,
    OPUSMajor,
    PGCMajor,
    PostAPI,
    UnknownMajor,
    UserAPI,
    VideoMajor,
)
from .retry import ApiCode352Error, retry_for_352
from .scheduler import BiliBangumiSite, BilibiliSite, BililiveSite


class _ProcessedText(NamedTuple):
    title: str
    content: str


class _ParsedMojarPost(NamedTuple):
    title: str
    content: str
    pics: list[str]
    url: str | None = None


class Bilibili(NewMessage):
    categories: ClassVar[dict[Category, str]] = {
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
        res = await client.get("https://api.live.bilibili.com/live_user/v1/Master/info", params={"uid": target})
        res.raise_for_status()
        res_data = type_validate_json(UserAPI, res.content)
        if res_data.code != 0:
            return None
        return res_data.data.info.uname if res_data.data else None

    @classmethod
    async def parse_target(cls, target_text: str) -> Target:
        if re.match(r"\d+", target_text):
            return Target(target_text)
        elif re.match(r"UID:(\d+)", target_text):
            return Target(target_text[4:])
        elif m := re.match(r"(?:https?://)?space\.bilibili\.com/(\d+)", target_text):
            return Target(m.group(1))
        else:
            raise cls.ParseTargetException(
                prompt="正确格式:\n1. 用户纯数字id\n2. UID:<用户id>\n3. 用户主页链接: https://space.bilibili.com/xxxx"
            )

    @retry_for_352
    async def get_sub_list(self, target: Target) -> list[DynRawPost]:
        client = await self.ctx.get_client(target)
        params = {"host_mid": target, "timezone_offset": -480, "offset": "", "features": "itemOpusStyle"}
        res = await client.get(
            "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space",
            params=params,
            timeout=4.0,
        )
        res.raise_for_status()
        try:
            res_obj = type_validate_json(PostAPI, res.content)
        except ValidationError as e:
            logger.exception("解析B站动态列表失败")
            logger.error(res.json())
            raise ApiError(res.request.url) from e

        # 0: 成功
        # -352: 需要cookie
        if res_obj.code == 0:
            if (data := res_obj.data) and (items := data.items):
                logger.trace(f"获取用户{target}的动态列表成功，共{len(items)}条动态")
                logger.trace(f"用户{target}的动态列表: {':'.join(x.id_str or x.basic.rid_str for x in items)}")
                return [item for item in items if item.type != "DYNAMIC_TYPE_NONE"]

            logger.trace(f"获取用户{target}的动态列表成功，但是没有动态")
            return []
        elif res_obj.code == -352:
            raise ApiCode352Error(res.request.url)
        else:
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
            for node in desc.rich_text_nodes:
                if (node_type := node.get("type", None)) and node_type == "RICH_TEXT_NODE_TYPE_TOPIC":
                    tags.append(node["text"].strip("#"))
        return tags

    def _text_process(self, dynamic: str, desc: str, title: str) -> _ProcessedText:
        # 计算视频标题和视频描述相似度
        title_similarity = 0.0 if len(title) == 0 or len(desc) == 0 else text_similarity(title, desc[: len(title)])
        if title_similarity > 0.9:
            desc = desc[len(title) :].lstrip()
        # 计算视频描述和动态描述相似度
        content_similarity = 0.0 if len(dynamic) == 0 or len(desc) == 0 else text_similarity(dynamic, desc)
        if content_similarity > 0.8:
            # 选择较长的描述
            return _ProcessedText(title, desc if len(dynamic) < len(desc) else dynamic)
        else:
            return _ProcessedText(title, f"{desc}" + (f"\n=================\n{dynamic}" if dynamic else ""))

    def pre_parse_by_mojar(self, raw_post: DynRawPost) -> _ParsedMojarPost:
        dyn = raw_post.modules.module_dynamic

        match raw_post.modules.module_dynamic.major:
            case VideoMajor(archive=archive):
                desc_text = dyn.desc.text if dyn.desc else ""
                parsed = self._text_process(desc_text, archive.desc, archive.title)
                return _ParsedMojarPost(
                    title=parsed.title,
                    content=parsed.content,
                    pics=[archive.cover],
                    url=URL(archive.jump_url).with_scheme("https").human_repr(),
                )
            case LiveRecommendMajor(live_rcmd=live_rcmd):
                live_play_info = type_validate_json(LiveRecommendMajor.Content, live_rcmd.content).live_play_info
                return _ParsedMojarPost(
                    title=live_play_info.title,
                    content=f"{live_play_info.parent_area_name} {live_play_info.area_name}",
                    pics=[live_play_info.cover],
                    url=URL(live_play_info.link).with_scheme("https").with_query(None).human_repr(),
                )
            case LiveMajor(live=live):
                return _ParsedMojarPost(
                    title=live.title,
                    content=f"{live.desc_first}\n{live.desc_second}",
                    pics=[live.cover],
                    url=URL(live.jump_url).with_scheme("https").human_repr(),
                )
            case ArticleMajor(article=article):
                return _ParsedMojarPost(
                    title=article.title,
                    content=article.desc,
                    pics=article.covers,
                    url=URL(article.jump_url).with_scheme("https").human_repr(),
                )
            case DrawMajor(draw=draw):
                return _ParsedMojarPost(
                    title="",
                    content=dyn.desc.text if dyn.desc else "",
                    pics=[item.src for item in draw.items],
                    url=f"https://t.bilibili.com/{raw_post.id_str}",
                )
            case PGCMajor(pgc=pgc):
                return _ParsedMojarPost(
                    title=pgc.title,
                    content="",
                    pics=[pgc.cover],
                    url=URL(pgc.jump_url).with_scheme("https").human_repr(),
                )
            case OPUSMajor(opus=opus):
                return _ParsedMojarPost(
                    title=opus.title or "",
                    content=opus.summary.text,
                    pics=[pic.url for pic in opus.pics],
                    url=URL(opus.jump_url).with_scheme("https").human_repr(),
                )
            case CommonMajor(common=common):
                return _ParsedMojarPost(
                    title=common.title,
                    content=common.desc,
                    pics=[common.cover],
                    url=URL(common.jump_url).with_scheme("https").human_repr(),
                )
            case CoursesMajor(courses=courses):
                return _ParsedMojarPost(
                    title=courses.title,
                    content=f"{courses.sub_title}\n{courses.desc}",
                    pics=[courses.cover],
                    url=URL(courses.jump_url).with_scheme("https").human_repr(),
                )
            case DeletedMajor(none=none):
                return _ParsedMojarPost(
                    title="",
                    content=none.tips,
                    pics=[],
                    url=None,
                )
            case UnknownMajor(type=unknown_type):
                logger.error(f"无法解析的动态，类型: {unknown_type}")
                return _ParsedMojarPost(
                    title="",
                    content=f"无法解析的动态，类型: {unknown_type}",
                    pics=[],
                    url=f"https://t.bilibili.com/{raw_post.id_str}",
                )
            case None:  # 没有major的情况
                return _ParsedMojarPost(
                    title="",
                    content=dyn.desc.text if dyn.desc else "",
                    pics=[],
                    url=f"https://t.bilibili.com/{raw_post.id_str}",
                )
            case _:
                raise CategoryNotSupport(f"{raw_post.id_str=}")

    async def parse(self, raw_post: DynRawPost) -> Post:
        parsed_raw_post = self.pre_parse_by_mojar(raw_post)
        parsed_raw_repost = None
        if self._do_get_category(raw_post.type) == Category(5):
            match raw_post.orig:
                case PostAPI.Item() as orig:
                    parsed_raw_repost = self.pre_parse_by_mojar(orig)
                case PostAPI.DeletedItem() as orig:
                    parsed_raw_repost = self.pre_parse_by_mojar(orig.to_item())
                case None:
                    logger.warning(f"转发动态{raw_post.id_str}没有原动态")

        post = Post(
            self,
            content=decode_unicode_escapes(parsed_raw_post.content),
            title=parsed_raw_post.title,
            images=list(parsed_raw_post.pics),
            timestamp=self.get_date(raw_post),
            url=parsed_raw_post.url,
            avatar=raw_post.modules.module_author.face,
            nickname=raw_post.modules.module_author.name,
        )
        if parsed_raw_repost:
            match raw_post.orig:
                case PostAPI.Item() as orig:
                    orig = orig
                case PostAPI.DeletedItem() as orig:
                    orig = orig.to_item()
                case None:
                    raise ValueError("转发动态没有原动态")

            post.repost = Post(
                self,
                content=decode_unicode_escapes(parsed_raw_repost.content),
                title=parsed_raw_repost.title,
                images=list(parsed_raw_repost.pics),
                timestamp=self.get_date(orig),
                url=parsed_raw_repost.url,
                avatar=orig.modules.module_author.face,
                nickname=orig.modules.module_author.name,
            )
        return post


class Bilibililive(StatusChange):
    categories: ClassVar[dict[Category, str]] = {1: "开播提醒", 2: "标题更新提醒", 3: "下播提醒"}
    platform_name = "bilibili-live"
    enable_tag = False
    enabled = True
    is_common = True
    site = BililiveSite
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
        res = await client.get("https://api.live.bilibili.com/live_user/v1/Master/info", params={"uid": target})
        res.raise_for_status()
        res_data = type_validate_json(UserAPI, res.content)
        if res_data.code != 0:
            return None
        return res_data.data.info.uname if res_data.data else None

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
        # 开播提醒固定使用封面 否则优先使用关键帧，没有则使用封面
        pic = [raw_post.cover] if raw_post.category == Category(1) else [raw_post.keyframe or raw_post.cover]
        title = f"[{self.categories[raw_post.category].rstrip('提醒')}] {raw_post.title}"
        target_name = f"{raw_post.uname} {raw_post.area_name}"
        return Post(
            self,
            content="",
            title=title,
            url=url,
            images=list(pic),
            nickname=target_name,
            compress=True,
        )


class BilibiliBangumi(StatusChange):
    categories: ClassVar[dict[Category, str]] = {}
    platform_name = "bilibili-bangumi"
    enable_tag = False
    enabled = True
    is_common = True
    site = BiliBangumiSite
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
        detail_res = await client.get(f"https://api.bilibili.com/pgc/view/web/season?season_id={raw_post['season_id']}")
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
            content=content,
            title=title,
            url=url,
            images=list(pic),
            nickname=target_name,
            compress=True,
        )


model_rebuild(Bilibililive.Info)
