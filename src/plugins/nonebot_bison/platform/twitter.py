import random
from typing import Any, Optional

import httpx
from httpx import AsyncClient, Response
from nonebot.log import logger

from ..post import Post
from ..types import Category, RawPost, Target
from ..utils import SchedulerConfig
from .platform import NewMessage


class TwitterSchedConf(SchedulerConfig):
    name = "twitter.com"
    schedule_type = "interval"
    schedule_setting = {"seconds": 30}


class Twitter(NewMessage):
    categories = {}
    platform_name = "twitter"
    name = "推特"
    enable_tag = False
    enabled = True
    is_common = True
    scheduler = TwitterSchedConf
    has_target = True

    _cookie = None
    _authorization = "Bearer AAAAAAAAAAAAAAAAAAAAAPYXBAAAAAAACLXUNDekMxqa8h%2F40K4moUkGsoc%3DTYfbDKbT3jJPCEVnMYqilB28NHfOPqkca3qaAxGfsyKCs0wRbw"
    _header: dict[str, str] = {
        "authorization": _authorization,
        "x-twitter-client-language": "en",
        "x-twitter-active-user": "yes",
        "Referer": "https://twitter.com/",
    }

    @classmethod
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        ...  # TODO

    async def get_sub_list(self, _) -> list[RawPost]:
        ...  # TODO

    def get_id(self, post: RawPost) -> Any:
        ...  # TODO

    def get_date(self, _: RawPost) -> None:
        ...  # TODO

    async def parse(self, raw_post: RawPost) -> Post:
        ...  # TODO

    def get_category(self, post: RawPost) -> Optional[Category]:
        ...  # TODO

    # ref: https://github.com/DIYgod/RSSHub/blob/master/lib/v2/twitter/web-api/twitter-got.js
    async def _request(
        self, url: str, method: str, params: dict[str, str] = None
    ) -> Response:
        await self._reset_session()
        resp = await self._got(method, url, params=params)
        if resp.status_code == 403:
            await self._reset_session(force=True)
            resp = await self._got(method, url, params=params)
        elif resp.status_code != 200:
            logger.warning(f"unable to request with status code {resp.status_code}")
        return resp

    async def _reset_session(self, force=False):
        if self._cookie and not force:
            return
        csrf_token = hex(random.getrandbits(128))[2:]
        self._cookie = httpx.Cookies()
        self._cookie.set(name="ct0", value=csrf_token, domain="twitter.com")
        self._header["x-csrf-token"] = csrf_token

        # First request to get guest-token
        resp = await self._got(
            "https://api.twitter.com/1.1/guest/activate.json", "POST"
        )
        guest_token = resp.json()["guest_token"]
        self._header["x-guest-token"] = guest_token
        self._cookie.set(name="gt", value=guest_token, domain="twitter.com")

        # Second request to get _twitter_sess
        await self._got(
            "https://twitter.com/i/js_inst", "GET", {"c_name": "ui_metrics"}
        )

    async def _got(
        self,
        url: str,
        method: str,
        params: dict[str, str] = None,
        headers: dict[str, str] = None,
    ) -> Response:
        full_headers = self._header | (headers if headers else {})
        cookies = self._cookie
        resp = await self.client.request(
            method, url, params=params, headers=full_headers, cookies=cookies
        )
        self._cookie.update(resp.cookies)
        csrf_token = resp.cookies.get("ct0")
        if csrf_token:
            self._header["x-csrf-token"] = csrf_token
        return resp
