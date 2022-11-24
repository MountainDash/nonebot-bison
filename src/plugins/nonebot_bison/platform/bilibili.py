import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from httpx import AsyncClient
from nonebot.log import logger
from typing_extensions import Self

from ..post import Post
from ..types import ApiError, Category, RawPost, Tag, Target
from ..utils import SchedulerConfig
from .platform import CategoryNotSupport, NewMessage, StatusChange


class BilibiliSchedConf(SchedulerConfig):

    name = "bilibili.com"
    schedule_type = "interval"
    schedule_setting = {"seconds": 10}

    _client_refresh_time: datetime
    cookie_expire_time = timedelta(hours=5)

    def __init__(self):
        self._client_refresh_time = datetime(
            year=2000, month=1, day=1
        )  # an expired time
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
        5: "转发"
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
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        res = await client.get(
            "https://api.bilibili.com/x/space/acc/info", params={"mid": target}
        )
        res_data = json.loads(res.text)
        if res_data["code"]:
            return None
        return res_data["data"]["name"]

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
        res_dict = json.loads(res.text)
        if res_dict["code"] == 0:
            return res_dict["data"].get("cards")
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
        raise CategoryNotSupport()

    def get_category(self, post: RawPost) -> Category:
        post_type = post["desc"]["type"]
        return self._do_get_category(post_type)

    def get_tags(self, raw_post: RawPost) -> list[Tag]:
        return [
            *map(
                lambda tp: tp["topic_name"],
                raw_post["display"]["topic_info"]["topic_details"],
            )
        ]

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
            text = card["dynamic"]
            pic = [card["pic"]]
        elif post_type == 4:
            # 纯文字
            text = card["item"]["content"]
            pic = []
        else:
            raise CategoryNotSupport()
        return text, pic

    async def parse(self, raw_post: RawPost) -> Post:
        card_content = json.loads(raw_post["card"])
        post_type = self.get_category(raw_post)
        target_name = raw_post["desc"]["user_profile"]["info"]["uname"]
        if post_type >= 1 and post_type < 5:
            url = ""
            if post_type == 1:
                # 一般动态
                url = "https://t.bilibili.com/{}".format(
                    raw_post["desc"]["dynamic_id_str"]
                )
            elif post_type == 2:
                # 专栏文章
                url = "https://www.bilibili.com/read/cv{}".format(
                    raw_post["desc"]["rid"]
                )
            elif post_type == 3:
                # 视频
                url = "https://www.bilibili.com/video/{}".format(
                    raw_post["desc"]["bvid"]
                )
            elif post_type == 4:
                # 纯文字
                url = "https://t.bilibili.com/{}".format(
                    raw_post["desc"]["dynamic_id_str"]
                )
            text, pic = self._get_info(post_type, card_content)
        elif post_type == 5:
            # 转发
            url = "https://t.bilibili.com/{}".format(raw_post["desc"]["dynamic_id_str"])
            text = card_content["item"]["content"]
            orig_type = card_content["item"]["orig_type"]
            orig = json.loads(card_content["origin"])
            orig_text, _ = self._get_info(self._do_get_category(orig_type), orig)
            text += "\n--------------\n"
            text += orig_text
            pic = []
        else:
            raise CategoryNotSupport(post_type)
        return Post("bilibili", text=text, url=url, pics=pic, target_name=target_name)


class Bilibililive(StatusChange):
    # Author : Sichongzou
    # Date : 2022-5-18 8:54
    # Description : bilibili开播提醒
    # E-mail : 1557157806@qq.com
    categories = {1: "开播提醒", 2: "标题更新提醒"}
    platform_name = "bilibili-live"
    enable_tag = False
    enabled = True
    is_common = True
    scheduler = BilibiliSchedConf
    name = "Bilibili直播"
    has_target = True

    @dataclass
    class Info:
        uname: str
        live_status: int
        room_id: str
        title: str
        cover_from_user: str
        keyframe: str
        category: Category = field(default=Category(0))

        def __init__(self, raw_info: dict):
            self.__dict__.update(raw_info)

        def is_live_turn_on(self, old_info: Self) -> bool:
            # 使用 & 判断直播开始
            # live_status:
            # 0:关播
            # 1:直播中
            # 2:轮播中
            if self.live_status == 1 and old_info.live_status != self.live_status:
                return True

            return False

        def is_title_update(self, old_info: Self) -> bool:
            # 使用 ^ 判断直播时标题改变
            if self.live_status == 1 and old_info.title != self.title:
                return True

            return False

    @classmethod
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        res = await client.get(
            "https://api.bilibili.com/x/space/acc/info", params={"mid": target}
        )
        res_data = json.loads(res.text)
        if res_data["code"]:
            return None
        return res_data["data"]["name"]

    async def get_status(self, target: Target) -> Info:
        params = {"uids[]": target}
        # from https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/live/info.md#%E6%89%B9%E9%87%8F%E6%9F%A5%E8%AF%A2%E7%9B%B4%E6%92%AD%E9%97%B4%E7%8A%B6%E6%80%81
        res = await self.client.get(
            "https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids",
            params=params,
            timeout=4.0,
        )
        res_dict = json.loads(res.text)
        if res_dict["code"] == 0:
            data = res_dict["data"][target]

            info = self.Info(data)

            return info
        else:
            raise self.FetchError()

    def compare_status(
        self, target: Target, old_status: Info, new_status: Info
    ) -> list[RawPost]:
        if new_status.is_live_turn_on(old_status):
            # 判断开播 运算符左右有顺序要求
            current_status = deepcopy(new_status)
            current_status.category = Category(1)
            return [current_status]
        elif new_status.is_title_update(old_status):
            # 判断直播时直播间标题变更 运算符左右有顺序要求
            current_status = deepcopy(new_status)
            current_status.category = Category(2)
            return [current_status]
        else:
            return []

    def get_category(self, status: Info) -> Category:
        assert status.category != Category(0)
        return status.category

    async def parse(self, raw_info: Info) -> Post:
        url = "https://live.bilibili.com/{}".format(raw_info.room_id)
        pic = [raw_info.keyframe]
        target_name = raw_info.uname
        title = raw_info.title
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
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
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
            return Target(m.group(1))
        elif m := re.match(
            r"(?:https?://)?www\.bilibili\.com/bangumi/media/md(\d+)/", target_string
        ):
            return Target(m.group(1))
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
