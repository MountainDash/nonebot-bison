from abc import abstractmethod
import time
from collections import defaultdict
from typing import Any, Collection, Optional

import httpx
from nonebot import logger

from ..plugin_config import plugin_config
from ..post import Post
from ..types import Category, RawPost, Tag, Target, User, UserSubInfo


class CategoryNotSupport(Exception):
    "raise in get_category, when post category is not supported"


class RegistryMeta(type):

    def __new__(cls, name, bases, namespace, **kwargs):
        if name not in ['PlatformProto', 'Platform', 'PlatformNoTarget'] and \
                'platform_name' not in namespace:
            raise TypeError('Platform has no `platform_name`')
        return super().__new__(cls, name, bases, namespace, **kwargs)

    def __init__(cls, name, bases, namespace, **kwargs):
        if not hasattr(cls, 'registory'):
            # this is the base class
            cls.registory = []
        elif name not in ['Platform', 'PlatformNoTarget']:
            # this is the subclass
            cls.registory.append(cls)

        super().__init__(name, bases, namespace, **kwargs)


class PlatformProto(metaclass=RegistryMeta):

    categories: dict[Category, str]
    reverse_category: dict[str, Category]
    has_target: bool
    platform_name: str
    name: str
    enable_tag: bool
    cache: dict[Any, Post]
    enabled: bool
    is_common: bool
    schedule_interval: int

    @abstractmethod
    async def fetch_new_post(self, target: Target, users: list[UserSubInfo]) -> list[tuple[User, list[Post]]]:
        ...

    @staticmethod
    @abstractmethod
    async def get_account_name(target: Target) -> Optional[str]:
        "return the username(name) of the target"

    @abstractmethod
    def get_id(self, post: RawPost) -> Any:
        "Get post id of given RawPost"

    @abstractmethod
    def get_date(self, post: RawPost) -> Optional[int]:
        "Get post timestamp and return, return None if can't get the time"

    @abstractmethod
    def get_category(self, post: RawPost) -> Optional[Category]:
        "Return category of given Rawpost"
        raise NotImplementedError()

    @abstractmethod
    def get_tags(self, raw_post: RawPost) -> Optional[Collection[Tag]]:
        "Return Tag list of given RawPost"

    @abstractmethod
    async def parse(self, raw_post: RawPost) -> Post:
        "parse RawPost into post"

    @abstractmethod
    def filter_platform_custom(self, post: RawPost) -> bool:
        "a customed filter"
        raise NotImplementedError()

    async def _parse_with_cache(self, post: RawPost) -> Post:
        post_id = self.get_id(post)
        if post_id not in self.cache:
            retry_times = 3
            while retry_times:
                try:
                    self.cache[post_id] = await self.parse(post)
                    break
                except Exception as err:
                    if not retry_times:
                        raise err
                    retry_times -= 1
        return self.cache[post_id]

    def _do_filter_common(self, raw_post_list: list[RawPost], exists_posts_set: set) -> list[RawPost]:
        res = []
        for raw_post in raw_post_list:
            post_id = self.get_id(raw_post)
            if post_id in exists_posts_set:
                continue
            if (post_time := self.get_date(raw_post)) and time.time() - post_time > 2 * 60 * 60 and \
                    plugin_config.hk_reporter_init_filter:
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
            exists_posts_set.add(post_id)
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

    @abstractmethod
    async def get_sub_list(self, target: Target) -> list[RawPost]:
        "Get post list of the given target"

    async def filter_common(self, target: Target, raw_post_list: list[RawPost]) -> list[RawPost]:
        if not self.inited.get(target, False) and plugin_config.hk_reporter_init_filter:
            # target not init
            for raw_post in raw_post_list:
                post_id = self.get_id(raw_post)
                self.exists_posts[target].add(post_id)
            logger.info('init {}-{} with {}'.format(self.platform_name, target, self.exists_posts[target]))
            self.inited[target] = True
            return []
        return self._do_filter_common(raw_post_list, self.exists_posts[target])

    async def fetch_new_post(self, target: Target, users: list[UserSubInfo]) -> list[tuple[User, list[Post]]]:
        try:
            post_list = await self.get_sub_list(target)
            new_posts = await self.filter_common(target, post_list)
            res: list[tuple[User, list[Post]]] = []
            if not new_posts:
                return []
            else:
                for post in new_posts:
                    logger.info('fetch new post from {} {}: {}'.format(self.platform_name, target, self.get_id(post)))
            for user, category_getter, tag_getter in users:
                required_tags = tag_getter(target) if self.enable_tag else []
                cats = category_getter(target)
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

    async def get_sub_list(self) -> list[RawPost]:
        "Get post list of the given target"
        raise NotImplementedError()

    def __init__(self):
        self.exists_posts = set()
        self.inited = False
        self.reverse_category = {}
        self.cache: dict[Any, Post] = {}
        for key, val in self.categories.items():
            self.reverse_category[val] = key

    async def filter_common(self, raw_post_list: list[RawPost]) -> list[RawPost]:
        if not self.inited and plugin_config.hk_reporter_init_filter:
            # target not init
            for raw_post in raw_post_list:
                post_id = self.get_id(raw_post)
                self.exists_posts.add(post_id)
            logger.info('init {} with {}'.format(self.platform_name, self.exists_posts))
            self.inited = True
            return []
        return self._do_filter_common(raw_post_list, self.exists_posts)

    async def fetch_new_post(self, _: Target, users: list[UserSubInfo]) -> list[tuple[User, list[Post]]]:
        try:
            post_list = await self.get_sub_list()
            new_posts = await self.filter_common(post_list)
            res: list[tuple[User, list[Post]]] = []
            if not new_posts:
                return []
            else:
                for post in new_posts:
                    logger.info('fetch new post from {}: {}'.format(self.platform_name, self.get_id(post)))
            for user, category_getter, tag_getter in users:
                required_tags = tag_getter(Target('default'))
                cats = category_getter(Target('default'))
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
