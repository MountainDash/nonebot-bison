import re
import json
from typing import Any
from copy import deepcopy
from enum import Enum, unique
from typing_extensions import Self
from datetime import datetime, timedelta

from httpx import AsyncClient
from nonebot.log import logger
from pydantic import Field, BaseModel

from ..post import Post
from ..utils import SchedulerConfig, text_similarity
from ..types import Tag, Target, RawPost, ApiError, Category
from .platform import NewMessage, StatusChange, CategoryNotSupport, CategoryNotRecognize


class BilibiliSchedConf(SchedulerConfig):
    name = "bilibili.com"
    schedule_type = "interval"
    schedule_setting = {"seconds": 10}

    _client_refresh_time: datetime
    cookie_expire_time = timedelta(hours=5)

    def __init__(self):
        self._client_refresh_time = datetime(year=2000, month=1, day=1)  # an expired time
        super().__init__()

    async def _init_session(self):
        res = await self.default_http_client.get("https://www.bilibili.com/")
        if res.status_code != 200:
            logger.warning("unable to refresh temp cookie")
        else:
            self._client_refresh_time = datetime.now()

    async def _refresh_client(self):
        if datetime.now() - self._client_refresh_time > self.cookie_expire_time:
            await self._init_session()

    async def get_client(self, target: Target) -> AsyncClient:
        await self._refresh_client()
        return await super().get_client(target)

    async def get_query_name_client(self) -> AsyncClient:
        await self._refresh_client()
        return await super().get_query_name_client()


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
        res_data = res.json()
        if res_data["code"]:
            return None
        return res_data["data"]["card"]["name"]

    @classmethod
    async def parse_target(cls, target_text: str) -> Target:
        if re.match(r"\d+", target_text):
            return Target(target_text)
        elif m := re.match(r"(?:https?://)?space\.bilibili\.com/(\d+)", target_text):
            return Target(m.group(1))
        else:
            raise cls.ParseTargetException()

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        params = {"host_uid": target, "offset": 0, "need_top": 0}
        res = await self.client.get(
            "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history",
            params=params,
            timeout=4.0,
        )
        res.raise_for_status()
        res_dict = res.json()
        if res_dict["code"] == 0:
            return res_dict["data"].get("cards", [])
        else:
            raise ApiError(res.request.url)

    def get_id(self, post: RawPost) -> Any:
        return post["desc"]["dynamic_id"]

    def get_date(self, post: RawPost) -> int:
        return post["desc"]["timestamp"]

    def _do_get_category(self, post_type: int) -> Category:
        if post_type == 2:
            return Category(1)
        elif post_type == 64:
            return Category(2)
        elif post_type == 8:
            return Category(3)
        elif post_type == 4:
            return Category(4)
        elif post_type == 1:
            # 转发
            return Category(5)
        raise CategoryNotRecognize(post_type)

    def get_category(self, post: RawPost) -> Category:
        post_type = post["desc"]["type"]
        return self._do_get_category(post_type)

    def get_tags(self, raw_post: RawPost) -> list[Tag]:
        return [*(tp["topic_name"] for tp in raw_post["display"]["topic_info"]["topic_details"])]

    def _get_info(self, post_type: Category, card) -> tuple[str, list]:
        if post_type == 1:
            # 一般动态
            text = card["item"]["description"]
            pic = [img["img_src"] for img in card["item"]["pictures"]]
        elif post_type == 2:
            # 专栏文章
            text = "{} {}".format(card["title"], card["summary"])
            pic = card["image_urls"]
        elif post_type == 3:
            # 视频
            dynamic = card.get("dynamic", "")
            title = card["title"]
            desc = card.get("desc", "")

            if text_similarity(desc, dynamic) > 0.8:
                # 如果视频简介和动态内容相似，就只保留长的那个
                if len(dynamic) > len(desc):
                    text = f"{dynamic}\n=================\n{title}"
                else:
                    text = f"{title}\n\n{desc}"
            else:
                # 否则就把两个拼起来
                text = f"{dynamic}\n=================\n{title}\n\n{desc}"

            pic = [card["pic"]]
        elif post_type == 4:
            # 纯文字
            text = card["item"]["content"]
            pic = []
        else:
            raise CategoryNotSupport(post_type)
        return text, pic

    async def parse(self, raw_post: RawPost) -> Post:
        card_content = json.loads(raw_post["card"])
        post_type = self.get_category(raw_post)
        target_name = raw_post["desc"]["user_profile"]["info"]["uname"]
        if post_type >= 1 and post_type < 5:
            url = ""
            if post_type == 1:
                # 一般动态
                url = "https://t.bilibili.com/{}".format(raw_post["desc"]["dynamic_id_str"])
            elif post_type == 2:
                # 专栏文章
                url = "https://www.bilibili.com/read/cv{}".format(raw_post["desc"]["rid"])
            elif post_type == 3:
                # 视频
                url = "https://www.bilibili.com/video/{}".format(raw_post["desc"]["bvid"])
            elif post_type == 4:
                # 纯文字
                url = "https://t.bilibili.com/{}".format(raw_post["desc"]["dynamic_id_str"])
            text, pic = self._get_info(post_type, card_content)
        elif post_type == 5:
            # 转发
            url = "https://t.bilibili.com/{}".format(raw_post["desc"]["dynamic_id_str"])
            text = card_content["item"]["content"]
            orig_type = card_content["item"]["orig_type"]
            orig = json.loads(card_content["origin"])
            orig_text, pic = self._get_info(self._do_get_category(orig_type), orig)
            text += "\n--------------\n"
            text += orig_text
        else:
            raise CategoryNotSupport(post_type)
        return Post("bilibili", text=text, url=url, pics=pic, target_name=target_name)


class Bilibililive(StatusChange):
    categories = {1: "开播提醒", 2: "标题更新提醒", 3: "下播提醒"}
    platform_name = "bilibili-live"
    enable_tag = False
    enabled = True
    is_common = True
    scheduler = BilibiliSchedConf
    name = "Bilibili直播"
    has_target = True

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

    async def get_status(self, target: Target) -> Info:
        params = {"uids[]": target}
        # https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/live/info.md#批量查询直播间状态
        res = await self.client.get(
            "https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids",
            params=params,
            timeout=4.0,
        )
        res_dict = res.json()

        if res_dict["code"] != 0:
            raise self.FetchError()

        data = res_dict.get("data")
        if not data:
            return self._gen_empty_info(uid=int(target))
        room_data = data[target]
        return self.Info.parse_obj(room_data)

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
            self.name,
            text=title,
            url=url,
            pics=list(pic),
            target_name=target_name,
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
                "index_show": res_dict["result"]["media"]["new_ep"]["index"],
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
        text = lastest_episode["share_copy"]
        return Post(
            self.name,
            text=text,
            url=url,
            pics=list(pic),
            target_name=target_name,
            compress=True,
        )


Bilibililive.Info.update_forward_refs()
