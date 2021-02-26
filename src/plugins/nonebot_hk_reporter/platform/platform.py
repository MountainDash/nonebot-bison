import time
from collections import defaultdict
from typing import Any, Optional

import httpx
from nonebot import logger

from ..config import Config
from ..post import Post
from ..types import Category, RawPost, Tag, Target, User
from ..utils import Singleton


class CategoryNotSupport(Exception):
    "raise in get_category, when post category is not supported"
    pass

class PlatformProto(metaclass=Singleton):

    categories: dict[Category, str]
    reverse_category: dict[str, Category]
    has_target: bool
    platform_name: str
    enable_tag: bool
    async def fetch_new_post(self, target: Target, users: list[User]) -> list[tuple[User, list[Post]]]:
        ...
    @staticmethod
    async def get_account_name(target: Target) -> Optional[str]:
        ...

class Platform(PlatformProto):
    "platform with target(account), like weibo, bilibili"

    categories: dict[Category, str]
    has_target: bool = True
    platform_name: str
    enable_tag: bool

    def __init__(self):
        self.exists_posts = defaultdict(set)
        self.inited = dict()
        self.reverse_category = {}
        self.cache: dict[Any, Post] = {}
        for key, val in self.categories.items():
            self.reverse_category[val] = key

    @staticmethod
    async def get_account_name(target: Target) -> Optional[str]:
        "Given a tareget, return the username(name) of the target"
        raise NotImplementedError()

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        "Get post list of the given target"
        raise NotImplementedError()

    def get_id(self, post: RawPost) -> Any:
        "Get post id of given RawPost"
        raise NotImplementedError()

    def get_date(self, post: RawPost) -> Optional[int]:
        "Get post timestamp and return, return None if can't get the time"
        raise NotImplementedError()

    def get_category(self, post: RawPost) -> Optional[Category]:
        "Return category of given Rawpost"
        raise NotImplementedError()

    def get_tags(self, raw_post: RawPost) -> Optional[list[Tag]]:
        "Return Tag list of given RawPost"
        raise NotImplementedError()

    async def parse(self, raw_post: RawPost) -> Post:
        "parse RawPost into post"
        raise NotImplementedError()

    def filter_platform_custom(self, post: RawPost) -> bool:
        raise NotImplementedError()

    async def _parse_with_cache(self, post: RawPost) -> Post:
        post_id = self.get_id(post)
        if post_id not in self.cache:
            self.cache[post_id] = await self.parse(post)
        return self.cache[post_id]

    async def filter_common(self, target: Target, raw_post_list: list[RawPost]) -> list[RawPost]:
        if not self.inited.get(target, False):
            # target not init
            for raw_post in raw_post_list:
                post_id = self.get_id(raw_post)
                self.exists_posts[target].add(post_id)
            logger.info('init {}-{} with {}'.format(self.platform_name, target, self.exists_posts[target]))
            self.inited[target] = True
            return []
        res: list[RawPost] = []
        for raw_post in raw_post_list:
            post_id = self.get_id(raw_post)
            if post_id in self.exists_posts[target]:
                continue
            if (post_time := self.get_date(raw_post)) and time.time() - post_time > 2 * 60 * 60:
                continue
            try:
                if not self.filter_platform_custom(raw_post):
                    continue
            except NotImplementedError:
                pass
            try:
                self.get_category(raw_post)
            except CategoryNotSupport:
                continue
            except NotImplementedError:
                pass
            res.append(raw_post)
            self.exists_posts[target].add(post_id)
        return res

    async def filter_user_custom(self, raw_post_list: list[RawPost], cats: list[Category], tags: list[Tag]) -> list[RawPost]:
        res: list[RawPost] = []
        for raw_post in raw_post_list:
            if self.categories:
                cat = self.get_category(raw_post)
                if cats and cat not in cats:
                    continue
            if self.enable_tag and tags:
                flag = False
                post_tags = self.get_tags(raw_post)
                for tag in post_tags:
                    if tag in tags:
                        flag = True
                        break
                if not flag:
                    continue
            res.append(raw_post)
        return res

    async def fetch_new_post(self, target: Target, users: list[User]) -> list[tuple[User, list[Post]]]:
        try:
            config = Config()
            post_list = await self.get_sub_list(target)
            new_posts = await self.filter_common(target, post_list)
            res: list[tuple[User, list[Post]]] = []
            if not new_posts:
                return []
            else:
                for post in new_posts:
                    logger.info('fetch new post from {} {}: {}'.format(self.platform_name, target, self.get_id(post)))
            for user in users:
                required_tags = config.get_sub_tags(self.platform_name, target, user.user_type, user.user) if self.enable_tag else []
                cats = config.get_sub_category(self.platform_name, target, user.user_type, user.user)
                user_raw_post = await self.filter_user_custom(new_posts, cats, required_tags)
                user_post: list[Post] = []
                for raw_post in user_raw_post:
                    user_post.append(await self._parse_with_cache(raw_post))
                res.append((user, user_post))
            self.cache = {}
            return res
        except httpx.RequestError as err:
            logger.warning("network connection error: {}, url: {}".format(type(err), err.request.url))
            return []


class PlatformNoTarget(PlatformProto):

    categories: dict[Category, str]
    has_target = False
    platform_name: str
    enable_tag: bool

    def __init__(self):
        self.exists_posts = set()
        self.inited = False
        self.reverse_category = {}
        self.cache: dict[Any, Post] = {}
        for key, val in self.categories.items():
            self.reverse_category[val] = key

    @staticmethod
    async def get_account_name(target: Target) -> Optional[str]:
        "return the username(name) of the target"
        raise NotImplementedError()

    async def get_sub_list(self) -> list[RawPost]:
        "Get post list of the given target"
        raise NotImplementedError()

    def get_id(self, post: RawPost) -> Any:
        "Get post id of given RawPost"
        raise NotImplementedError()

    def get_date(self, post: RawPost) -> Optional[int]:
        "Get post timestamp and return, return None if can't get the time"
        raise NotImplementedError()

    def get_category(self, post: RawPost) -> Optional[Category]:
        "Return category of given Rawpost"
        raise NotImplementedError()

    def get_tags(self, raw_post: RawPost) -> Optional[list[Tag]]:
        "Return Tag list of given RawPost"
        raise NotImplementedError()

    async def parse(self, raw_post: RawPost) -> Post:
        "parse RawPost into post"
        raise NotImplementedError()

    def filter_platform_custom(self, post: RawPost) -> bool:
        raise NotImplementedError()

    async def _parse_with_cache(self, post: RawPost) -> Post:
        post_id = self.get_id(post)
        if post_id not in self.cache:
            self.cache[post_id] = await self.parse(post)
        return self.cache[post_id]

    async def filter_common(self, raw_post_list: list[RawPost]) -> list[RawPost]:
        if not self.inited:
            # target not init
            for raw_post in raw_post_list:
                post_id = self.get_id(raw_post)
                self.exists_posts.add(post_id)
            logger.info('init {} with {}'.format(self.platform_name, self.exists_posts))
            self.inited = True
            return []
        res: list[RawPost] = []
        for raw_post in raw_post_list:
            post_id = self.get_id(raw_post)
            if post_id in self.exists_posts:
                continue
            if (post_time := self.get_date(raw_post)) and time.time() - post_time > 2 * 60 * 60:
                continue
            try:
                if not self.filter_platform_custom(raw_post):
                    continue
            except NotImplementedError:
                pass
            try:
                self.get_category(raw_post)
            except CategoryNotSupport:
                continue
            except NotImplementedError:
                pass
            res.append(raw_post)
            self.exists_posts.add(post_id)
        return res

    async def filter_user_custom(self, raw_post_list: list[RawPost], cats: list[Category], tags: list[Tag]) -> list[RawPost]:
        res: list[RawPost] = []
        for raw_post in raw_post_list:
            if self.categories:
                cat = self.get_category(raw_post)
                if cats and cat not in cats:
                    continue
            if self.enable_tag and tags:
                flag = False
                post_tags = self.get_tags(raw_post)
                for tag in post_tags:
                    if tag in tags:
                        flag = True
                        break
                if not flag:
                    continue
            res.append(raw_post)
        return res

    async def fetch_new_post(self, _: Target, users: list[User]) -> list[tuple[User, list[Post]]]:
        try:
            config = Config()
            post_list = await self.get_sub_list()
            new_posts = await self.filter_common(post_list)
            res: list[tuple[User, list[Post]]] = []
            if not new_posts:
                return []
            else:
                for post in new_posts:
                    logger.info('fetch new post from {}: {}'.format(self.platform_name, self.get_id(post)))
            for user in users:
                required_tags = config.get_sub_tags(self.platform_name, 'default', user.user_type, user.user) if self.enable_tag else []
                cats = config.get_sub_category(self.platform_name, 'default', user.user_type, user.user)
                user_raw_post = await self.filter_user_custom(new_posts, cats, required_tags)
                user_post: list[Post] = []
                for raw_post in user_raw_post:
                    user_post.append(await self._parse_with_cache(raw_post))
                res.append((user, user_post))
            self.cache = {}
            return res
        except httpx.RequestError as err:
            logger.warning("network connection error: {}, url: {}".format(type(err), err.request.url))
            return []
