import functools
import json
import re
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import httpx
from nonebot.log import logger

from ..post import Post
from ..types import Category, RawPost, Tag, Target
from ..utils import SchedulerConfig
from ..utils.http import http_args
from .platform import CategoryNotSupport, NewMessage, StatusChange


class BilibiliSchedConf(SchedulerConfig, name="bilibili.com"):

    schedule_type = "interval"
    schedule_setting = {"seconds": 10}


from .platform import CategoryNotSupport, NewMessage, StatusChange


class _BilibiliClient:

    _http_client: httpx.AsyncClient
    _client_refresh_time: Optional[datetime]
    cookie_expire_time = timedelta(hours=5)

    async def _init_session(self):
        self._http_client = httpx.AsyncClient(**http_args)
        res = await self._http_client.get("https://www.bilibili.com/")
        if res.status_code != 200:
            import ipdb

            ipdb.set_trace()
            logger.warning("unable to refresh temp cookie")
        else:
            self._client_refresh_time = datetime.now()

    async def _refresh_client(self):
        if (
            getattr(self, "_client_refresh_time", None) is None
            or datetime.now() - self._client_refresh_time
            > self.cookie_expire_time  # type:ignore
            or self._http_client is None
        ):
            await self._init_session()


class Bilibili(_BilibiliClient, NewMessage):

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
    scheduler_class = "bilibili.com"
    name = "B站"
    has_target = True
    parse_target_promot = "请输入用户主页的链接"

    def ensure_client(fun: Callable):  # type:ignore
        @functools.wraps(fun)
        async def wrapped(self, *args, **kwargs):
            await self._refresh_client()
            return await fun(self, *args, **kwargs)

        return wrapped

    @ensure_client
    async def get_target_name(self, target: Target) -> Optional[str]:
        res = await self._http_client.get(
            "https://api.bilibili.com/x/space/acc/info", params={"mid": target}
        )
        res_data = json.loads(res.text)
        if res_data["code"]:
            return None
        return res_data["data"]["name"]

    async def parse_target(self, target_text: str) -> Target:
        if re.match(r"\d+", target_text):
            return Target(target_text)
        elif m := re.match(r"(?:https?://)?space\.bilibili\.com/(\d+)", target_text):
            return Target(m.group(1))
        else:
            raise self.ParseTargetException()

    @ensure_client
    async def get_sub_list(self, target: Target) -> list[RawPost]:
        params = {"host_uid": target, "offset": 0, "need_top": 0}
        res = await self._http_client.get(
            "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history",
            params=params,
            timeout=4.0,
        )
        res_dict = json.loads(res.text)
        if res_dict["code"] == 0:
            return res_dict["data"].get("cards")
        else:
            return []

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


class Bilibililive(_BilibiliClient, StatusChange):
    # Author : Sichongzou
    # Date : 2022-5-18 8:54
    # Description : bilibili开播提醒
    # E-mail : 1557157806@qq.com
    categories = {}
    platform_name = "bilibili-live"
    enable_tag = False
    enabled = True
    is_common = True
    scheduler_class = "bilibili.com"
    name = "Bilibili直播"
    has_target = True

    def ensure_client(fun: Callable):  # type:ignore
        @functools.wraps(fun)
        async def wrapped(self, *args, **kwargs):
            await self._refresh_client()
            return await fun(self, *args, **kwargs)

        return wrapped

    @ensure_client
    async def get_target_name(self, target: Target) -> Optional[str]:
        res = await self._http_client.get(
            "https://api.bilibili.com/x/space/acc/info", params={"mid": target}
        )
        res_data = json.loads(res.text)
        if res_data["code"]:
            return None
        return res_data["data"]["name"]

    @ensure_client
    async def get_status(self, target: Target):
        params = {"mid": target}
        res = await self._http_client.get(
            "https://api.bilibili.com/x/space/acc/info",
            params=params,
            timeout=4.0,
        )
        res_dict = json.loads(res.text)
        if res_dict["code"] == 0:
            info = {}
            info["uid"] = res_dict["data"]["mid"]
            info["uname"] = res_dict["data"]["name"]
            info["live_state"] = res_dict["data"]["live_room"]["liveStatus"]
            info["room_id"] = res_dict["data"]["live_room"]["roomid"]
            info["title"] = res_dict["data"]["live_room"]["title"]
            info["cover"] = res_dict["data"]["live_room"]["cover"]
            return info
        else:
            raise self.FetchError()

    def compare_status(self, target: Target, old_status, new_status) -> list[RawPost]:
        if (
            new_status["live_state"] != old_status["live_state"]
            and new_status["live_state"] == 1
        ):
            return [new_status]
        else:
            return []

    async def parse(self, raw_post: RawPost) -> Post:
        url = "https://live.bilibili.com/{}".format(raw_post["room_id"])
        pic = [raw_post["cover"]]
        target_name = raw_post["uname"]
        title = raw_post["title"]
        return Post(
            self.name,
            text=title,
            url=url,
            pics=pic,
            target_name=target_name,
            compress=True,
        )


class BilibiliBangumi(_BilibiliClient, StatusChange):

    categories = {}
    platform_name = "bilibili-bangumi"
    enable_tag = False
    enabled = True
    is_common = True
    scheduler_class = "bilibili.com"
    name = "Bilibili剧集"
    has_target = True
    parse_target_promot = "请输入剧集主页"

    _url = "https://api.bilibili.com/pgc/review/user"

    def ensure_client(fun: Callable):  # type:ignore
        @functools.wraps(fun)
        async def wrapped(self, *args, **kwargs):
            await self._refresh_client()
            return await fun(self, *args, **kwargs)

        return wrapped

    @ensure_client
    async def get_target_name(self, target: Target) -> Optional[str]:
        res = await self._http_client.get(self._url, params={"media_id": target})
        res_data = res.json()
        if res_data["code"]:
            return None
        return res_data["result"]["media"]["title"]

    async def parse_target(self, target_string: str) -> Target:
        if re.match(r"\d+", target_string):
            return Target(target_string)
        elif m := re.match(r"md(\d+)", target_string):
            return Target(m.group(1))
        elif m := re.match(
            r"(?:https?://)?www\.bilibili\.com/bangumi/media/md(\d+)/", target_string
        ):
            return Target(m.group(1))
        raise self.ParseTargetException()

    @ensure_client
    async def get_status(self, target: Target):
        res = await self._http_client.get(
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

    @ensure_client
    async def parse(self, raw_post: RawPost) -> Post:
        detail_res = await self._http_client.get(
            f'http://api.bilibili.com/pgc/view/web/season?season_id={raw_post["season_id"]}'
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
        pic = [lastest_episode["cover"]]
        target_name = detail_dict["result"]["season_title"]
        text = lastest_episode["share_copy"]
        return Post(
            self.name,
            text=text,
            url=url,
            pics=pic,
            target_name=target_name,
            compress=True,
        )
