import random
import re
from datetime import datetime, timedelta, timezone
from json import JSONEncoder
from typing import Any, Collection, Literal, Optional, Union

import httpx
from httpx import AsyncClient, Response

from ..post import Post
from ..types import Category, RawPost, Tag, Target
from ..utils import SchedulerConfig
from .platform import NewMessage


class TwitterSchedConf(SchedulerConfig):
    name = "twitter.com"
    schedule_type = "interval"
    schedule_setting = {"seconds": 30}


class TwitterUtils:
    # 获取 Twitter 访问 session 需要的字段
    _cookie = None
    _authorization = "Bearer AAAAAAAAAAAAAAAAAAAAAPYXBAAAAAAACLXUNDekMxqa8h%2F40K4moUkGsoc%3DTYfbDKbT3jJPCEVnMYqilB28NHfOPqkca3qaAxGfsyKCs0wRbw"
    _header: dict[str, str] = {
        "authorization": _authorization,
        "x-twitter-client-language": "en",
        "x-twitter-active-user": "yes",
        "Referer": "https://twitter.com/",
    }

    # 构建 Twitter GraphQL 请求时需要的变量
    _variables: dict[str, Any] = {
        "count": 20,
        "includePromotedContent": False,
        "withSuperFollowsUserFields": True,
        "withBirdwatchPivots": False,
        "withDownvotePerspective": False,
        "withReactionsMetadata": False,
        "withReactionsPerspective": False,
        "withSuperFollowsTweetFields": True,
        "withClientEventToken": False,
        "withBirdwatchNotes": False,
        "withVoice": True,
        "withV2Timeline": False,
        "__fs_interactive_text": False,
        "__fs_dont_mention_me_view_api_enabled": False,
    }

    @classmethod
    async def get_user(cls, client: AsyncClient, target: Target) -> Response:
        """通过用户名获取用户数据"""
        return await cls.request(
            client,
            "https://twitter.com/i/api/graphql/hc-pka9A7gyS3xODIafnrQ/UserByScreenName",
            "GET",
            cls.make_variables({"screen_name": target, "withHighlightedLabel": True}),
        )

    @classmethod
    async def get_user_id(cls, client: AsyncClient, target: Target) -> int:
        """通过用户名获取用户 ID"""
        result = (await cls.get_user(client, target)).json()
        user_id = result["data"]["user"]["rest_id"]
        if isinstance(user_id, str):
            user_id = int(user_id)
        assert isinstance(user_id, int)
        return user_id

    @classmethod
    async def gather_legacy_from_data(cls, entries, filters: str = "tweet-") -> list:
        """将必要字段加入 legacy 版本，并返回 legacy 数据
        ref: https://github.com/DIYgod/RSSHub/blob/master/lib/v2/twitter/web-api/twitter-api.js
        """
        tweets = list()
        for entry in entries:
            if entry["entryId"] and filters in entry["entryId"]:
                try:
                    tweet = entry["content"]["itemContent"]["tweet_results"]["result"]
                except KeyError:
                    tweet = None
                if tweet:
                    try:
                        retweet = tweet["legacy"]["retweeted_status_result"]["result"]
                    except KeyError:
                        retweet = None
                    for t in [tweet, retweet]:
                        if not t:
                            continue
                        if not t["legacy"]:
                            continue
                        t["legacy"]["user"] = t["core"]["user_results"]["result"][
                            "legacy"
                        ]
                        try:
                            quote = t["quoted_status_result"]["result"]
                        except KeyError:
                            quote = None
                        if quote:
                            t["legacy"]["quoted_status"] = quote["legacy"]
                            t["legacy"]["quoted_status"]["user"] = quote["core"][
                                "user_results"
                            ]["result"]["legacy"]
                    legacy = tweet["legacy"]
                    if legacy:
                        if retweet:
                            legacy["retweeted_status"] = retweet["legacy"]
                        tweets.append(legacy)
        return tweets

    @classmethod
    async def timeline_tweets_and_replies(
        cls, client: AsyncClient, user_id: int, params: dict[str, Any] = None
    ):
        """返回用户最新的 count=20 条推文（含回复）"""
        if not params:
            params = {}
        return await cls.pagination_tweets(
            client,
            "/graphql/t4wEKVulW4Mbv1P0kgxTEw/UserTweetsAndReplies",
            user_id,
            params | {"withCommunity": True},
        )

    @classmethod
    async def pagination_tweets(
        cls, client: AsyncClient, endpoint: str, user_id: int, variables: dict[str, Any]
    ):
        """
        ref: https://github.com/DIYgod/RSSHub/blob/master/lib/v2/twitter/web-api/twitter-api.js
        """
        resp = await cls.request(
            client,
            f"https://twitter.com/i/api{endpoint}",
            "GET",
            cls.make_variables(variables | cls._variables | {"userId": user_id}),
        )
        data = resp.json()
        inst = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
        for i in inst:
            if i["type"] == "TimelineAddEntries":
                entries = i["entries"]
                assert isinstance(entries, list)
                return entries

    @classmethod
    async def request(
        cls,
        client: AsyncClient,
        url: str,
        method: str = "GET",
        params: dict[str, str] = None,
    ) -> Response:
        """包装了异常或初始化时重置 session 的请求函数
        ref: https://github.com/DIYgod/RSSHub/blob/master/lib/v2/twitter/web-api/twitter-got.js
        """
        await cls.reset_session(client)
        resp = await cls.got(client, url, method, params=params)
        if resp.status_code == 403:
            await cls.reset_session(client, force=True)
            resp = await cls.got(client, url, method, params=params)
        resp.raise_for_status()
        return resp

    @classmethod
    async def reset_session(cls, client: AsyncClient, force: bool = False):
        """重置访问 Twitter 的 session"""
        if cls._cookie and not force:
            return
        csrf_token = hex(random.getrandbits(128))[2:]
        cls._cookie = httpx.Cookies()
        cls._cookie.set(name="ct0", value=csrf_token, domain="twitter.com")
        cls._header["x-csrf-token"] = csrf_token

        # First request to get guest-token
        resp = await cls.got(
            client, "https://api.twitter.com/1.1/guest/activate.json", "POST"
        )
        resp.raise_for_status()
        guest_token = resp.json()["guest_token"]
        cls._header["x-guest-token"] = guest_token
        cls._cookie.set(name="gt", value=guest_token, domain="twitter.com")

        # Second request to get _twitter_sess
        (
            await cls.got(
                client, "https://twitter.com/i/js_inst", "GET", {"c_name": "ui_metrics"}
            )
        ).raise_for_status()

    @classmethod
    async def got(
        cls,
        client: AsyncClient,
        url: str,
        method: str,
        params: dict[str, str] = None,
        headers: dict[str, str] = None,
    ) -> Response:
        """核心请求函数"""
        full_headers = cls._header | (headers if headers else {})
        cookies = cls._cookie
        resp = await client.request(
            method, url, params=params, headers=full_headers, cookies=cookies
        )
        cls._cookie.update(resp.cookies)
        csrf_token = resp.cookies.get("ct0")
        if csrf_token:
            cls._header["x-csrf-token"] = csrf_token
        return resp

    @classmethod
    def make_variables(cls, params: dict[str, Any]) -> dict[str, str]:
        """构建 GraphQL 请求参数"""
        return {"variables": cls.encode(params)}

    @classmethod
    def encode(cls, params: dict[str, Any]) -> str:
        """JSON 格式化函数
        ref: https://github.com/mikf/gallery-dl/blob/8805bd38ab41dcbb6aba9799008fcb9363f1c0f5/gallery_dl/extractor/twitter.py#L1039
        """
        return JSONEncoder(separators=(",", ":")).encode(params)

    @classmethod
    def check_post_type(
        cls, raw_post: RawPost
    ) -> tuple[Literal["retweet", "quote", "reply", "original"], bool]:
        """检查推文，返回其对应的类型 str 以及是否包含媒体的 bool

        类型：retweet（转发）、quote（引文转发）、reply（回复）、original（原创）
        媒体：图片、视频
        """

        post_type: Literal["retweet", "quote", "reply", "original"]
        is_media = False
        pointers = [raw_post]

        if "retweeted_status" in raw_post:
            post_type = "retweet"
            pointers.append(raw_post["retweeted_status"])
        elif "quoted_status" in raw_post:
            post_type = "quote"
            pointers.append(raw_post["quoted_status"])
        elif "in_reply_to_screen_name" in raw_post:
            post_type = "reply"
        else:
            post_type = "original"

        for pointer in pointers:
            try:
                _ = pointer["extended_entities"]["media"]
                is_media = True
            except KeyError:
                continue

        assert post_type in ["retweet", "quote", "reply", "original"]
        assert is_media in [True, False]
        return post_type, is_media

    @classmethod
    def trim_url(
        cls, raw_text: str, entities: dict[str, Any], id_str_list: list[str]
    ) -> str:
        """除去推文结尾存在的无关链接，并将短链接还原为原始链接"""
        result = raw_text
        # Media
        if "media" in entities:
            for media in entities["media"]:
                url = media["url"]
                result = result.replace(url, "")

        # Quote
        for url_item in entities["urls"]:
            for id_str in id_str_list:
                if f"status/{id_str}" in url_item["expanded_url"]:
                    url = url_item["url"]
                    result = result.replace(url, "")

        # Recover URLs
        for url_item in entities["urls"]:
            old = url_item["url"]
            new = url_item["expanded_url"]
            result = result.replace(old, new)

        return result.strip()


class Twitter(NewMessage):
    categories = {1: "转发媒体", 2: "转发文字", 3: "回复媒体", 4: "回复文字", 5: "原创媒体", 6: "原创文字"}
    platform_name = "twitter"
    name = "推特"
    enable_tag = False
    enabled = True
    is_common = True
    scheduler = TwitterSchedConf
    has_target = True

    @classmethod
    async def get_target_name(
        cls, client: AsyncClient, target: Target
    ) -> Optional[str]:
        result = (await TwitterUtils.get_user(client, target)).json()
        user_info = result["data"]["user"]["legacy"]
        nickname = user_info["name"]
        assert isinstance(nickname, str)
        return nickname

    @classmethod
    async def parse_target(cls, target_string: str) -> Target:
        if "twitter.com/i/" in target_string:
            raise cls.ParseTargetException("暂不支持通过 id 获取用户名")
        if m := re.match(
            r"(?:https?://)?(?:.*\.)?twitter\.com/([a-zA-Z0-9_]+)(?:/.*)?",
            target_string,
        ):
            return Target(m.group(1))
        return Target(target_string)

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        user_id = await TwitterUtils.get_user_id(self.client, target)
        results = await TwitterUtils.gather_legacy_from_data(
            await TwitterUtils.timeline_tweets_and_replies(self.client, user_id, {})
        )
        return results

    def get_id(self, raw_post: RawPost) -> Any:
        return int(raw_post["id_str"])

    def get_date(self, raw_post: RawPost) -> float:
        # 'Wed Feb 08 13:20:10 +0000 2023'
        created_raw = raw_post["created_at"]
        created_time = datetime.strptime(
            created_raw, "%a %b %d %H:%M:%S +0000 %Y"
        ).replace(tzinfo=timezone(timedelta(0)))
        return created_time.timestamp()

    async def parse(self, raw_post: RawPost) -> Post:
        def get_parsed_text(status: dict[str, Any], need_quote: bool = False) -> str:
            scr_name = status["user"]["name"]
            id_str_list = [status["id_str"]]
            raw_text = status["full_text"]
            if "quoted_status_id_str" in status:
                id_str_list.append(status["quoted_status_id_str"])
            text = TwitterUtils.trim_url(raw_text, status["entities"], id_str_list)
            if need_quote:
                text = f"RT @{scr_name}:\n" + text
            return text

        # TODO: Extended Tweets, Polls, Spaces
        # TODO: Video media might be missing if tweets also have images
        template: str = get_parsed_text(raw_post)
        screen_name: str = raw_post["user"]["name"]
        url: str = f"https://twitter.com/i/web/status/{raw_post['id_str']}"
        images: list[Union[str, bytes]] = list()

        media_pointers = [raw_post]
        tweet_type, _ = TwitterUtils.check_post_type(raw_post)
        if tweet_type == "retweet":
            # 暂时不处理 retweet 为 quote 情况下的多层套娃引用
            retweet = raw_post["retweeted_status"]
            template = get_parsed_text(retweet, need_quote=True)

        elif tweet_type == "quote":
            quote = raw_post["quoted_status"]
            media_pointers.append(quote)
            template += "\n"
            template += get_parsed_text(quote, need_quote=True)

        for media_pointer in media_pointers:
            try:
                media_entities = media_pointer["extended_entities"]["media"]
            except KeyError:
                continue
            for item in media_entities:
                # TODO: 增加对 Animated GIF 与 Video 的支持
                if item["type"] != "photo":
                    continue
                media_url = item["media_url_https"]
                images.append(media_url)

        return Post(
            "twitter", text=template, url=url, pics=images, target_name=screen_name
        )

    def get_category(self, raw_post: RawPost) -> Optional[Category]:
        tweet_type, is_media = TwitterUtils.check_post_type(raw_post)
        if tweet_type in ["retweet", "quote"]:
            cat = 1
        elif tweet_type == "reply":
            cat = 3
        else:
            cat = 5

        if not is_media:
            cat += 1

        return Category(cat)

    def get_tags(self, raw_post: RawPost) -> Optional[Collection[Tag]]:
        tags = set()

        pointers = [raw_post]
        if "quoted_status" in raw_post:
            pointers.append(raw_post["quoted_status"])

        for pointer in pointers:
            for hashtag in pointer["entities"]["hashtags"]:
                tags.add(Tag(hashtag["text"]))

        return tags
