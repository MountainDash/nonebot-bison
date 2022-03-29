import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Collection, Literal, Optional

import httpx
from nonebot.log import logger

from ..plugin_config import plugin_config
from ..post import Post
from ..types import Category, RawPost, Tag, Target, User, UserSubInfo


class CategoryNotSupport(Exception):
    "raise in get_category, when post category is not supported"


class RegistryMeta(type):
    def __new__(cls, name, bases, namespace, **kwargs):
        return super().__new__(cls, name, bases, namespace)

    def __init__(cls, name, bases, namespace, **kwargs):
        if kwargs.get("base"):
            # this is the base class
            cls.registry = []
        elif not kwargs.get("abstract"):
            # this is the subclass
            cls.registry.append(cls)

        super().__init__(name, bases, namespace, **kwargs)


class RegistryABCMeta(RegistryMeta, ABC):
    ...


class Platform(metaclass=RegistryABCMeta, base=True):

    schedule_type: Literal["date", "interval", "cron"]
    schedule_kw: dict
    is_common: bool
    enabled: bool
    name: str
    has_target: bool
    categories: dict[Category, str]
    enable_tag: bool
    store: dict[Target, Any]
    platform_name: str

    @abstractmethod
    async def get_target_name(self, target: Target) -> Optional[str]:
        ...

    @abstractmethod
    async def fetch_new_post(
        self, target: Target, users: list[UserSubInfo]
    ) -> list[tuple[User, list[Post]]]:
        ...

    @abstractmethod
    async def parse(self, raw_post: RawPost) -> Post:
        ...

    async def do_parse(self, raw_post: RawPost) -> Post:
        "actually function called"
        return await self.parse(raw_post)

    def __init__(self):
        super().__init__()
        self.reverse_category = {}
        for key, val in self.categories.items():
            self.reverse_category[val] = key
        self.store = dict()

    @abstractmethod
    def get_tags(self, raw_post: RawPost) -> Optional[Collection[Tag]]:
        "Return Tag list of given RawPost"

    def get_stored_data(self, target: Target) -> Any:
        return self.store.get(target)

    def set_stored_data(self, target: Target, data: Any):
        self.store[target] = data

    async def filter_user_custom(
        self, raw_post_list: list[RawPost], cats: list[Category], tags: list[Tag]
    ) -> list[RawPost]:
        res: list[RawPost] = []
        for raw_post in raw_post_list:
            if self.categories:
                cat = self.get_category(raw_post)
                if cats and cat not in cats:
                    continue
            if self.enable_tag and tags:
                flag = False
                post_tags = self.get_tags(raw_post)
                for tag in post_tags or []:
                    if tag in tags:
                        flag = True
                        break
                if not flag:
                    continue
            res.append(raw_post)
        return res

    async def dispatch_user_post(
        self, target: Target, new_posts: list[RawPost], users: list[UserSubInfo]
    ) -> list[tuple[User, list[Post]]]:
        res: list[tuple[User, list[Post]]] = []
        for user, category_getter, tag_getter in users:
            required_tags = tag_getter(target) if self.enable_tag else []
            cats = category_getter(target)
            user_raw_post = await self.filter_user_custom(
                new_posts, cats, required_tags
            )
            user_post: list[Post] = []
            for raw_post in user_raw_post:
                user_post.append(await self.do_parse(raw_post))
            res.append((user, user_post))
        return res

    @abstractmethod
    def get_category(self, post: RawPost) -> Optional[Category]:
        "Return category of given Rawpost"
        raise NotImplementedError()


class MessageProcess(Platform, abstract=True):
    "General message process fetch, parse, filter progress"

    def __init__(self):
        super().__init__()
        self.parse_cache: dict[Any, Post] = dict()

    @abstractmethod
    def get_id(self, post: RawPost) -> Any:
        "Get post id of given RawPost"

    async def do_parse(self, raw_post: RawPost) -> Post:
        post_id = self.get_id(raw_post)
        if post_id not in self.parse_cache:
            retry_times = 3
            while retry_times:
                try:
                    self.parse_cache[post_id] = await self.parse(raw_post)
                    break
                except Exception as err:
                    retry_times -= 1
                    if not retry_times:
                        raise err
        return self.parse_cache[post_id]

    @abstractmethod
    async def get_sub_list(self, target: Target) -> list[RawPost]:
        "Get post list of the given target"

    @abstractmethod
    def get_date(self, post: RawPost) -> Optional[int]:
        "Get post timestamp and return, return None if can't get the time"

    async def filter_common(self, raw_post_list: list[RawPost]) -> list[RawPost]:
        res = []
        for raw_post in raw_post_list:
            # post_id = self.get_id(raw_post)
            # if post_id in exists_posts_set:
            #     continue
            if (
                (post_time := self.get_date(raw_post))
                and time.time() - post_time > 2 * 60 * 60
                and plugin_config.bison_init_filter
            ):
                continue
            try:
                self.get_category(raw_post)
            except CategoryNotSupport:
                continue
            except NotImplementedError:
                pass
            res.append(raw_post)
        return res


class NewMessage(MessageProcess, abstract=True):
    "Fetch a list of messages, filter the new messages, dispatch it to different users"

    @dataclass
    class MessageStorage:
        inited: bool
        exists_posts: set[Any]

    async def filter_common_with_diff(
        self, target: Target, raw_post_list: list[RawPost]
    ) -> list[RawPost]:
        filtered_post = await self.filter_common(raw_post_list)
        store = self.get_stored_data(target) or self.MessageStorage(False, set())
        res = []
        if not store.inited and plugin_config.bison_init_filter:
            # target not init
            for raw_post in filtered_post:
                post_id = self.get_id(raw_post)
                store.exists_posts.add(post_id)
            logger.info(
                "init {}-{} with {}".format(
                    self.platform_name, target, store.exists_posts
                )
            )
            store.inited = True
        else:
            for raw_post in filtered_post:
                post_id = self.get_id(raw_post)
                if post_id in store.exists_posts:
                    continue
                res.append(raw_post)
                store.exists_posts.add(post_id)
        self.set_stored_data(target, store)
        return res

    async def fetch_new_post(
        self, target: Target, users: list[UserSubInfo]
    ) -> list[tuple[User, list[Post]]]:
        try:
            post_list = await self.get_sub_list(target)
            new_posts = await self.filter_common_with_diff(target, post_list)
            if not new_posts:
                return []
            else:
                for post in new_posts:
                    logger.info(
                        "fetch new post from {} {}: {}".format(
                            self.platform_name,
                            target if self.has_target else "-",
                            self.get_id(post),
                        )
                    )
            res = await self.dispatch_user_post(target, new_posts, users)
            self.parse_cache = {}
            return res
        except httpx.RequestError as err:
            logger.warning(
                "network connection error: {}, url: {}".format(
                    type(err), err.request.url
                )
            )
            return []


class StatusChange(Platform, abstract=True):
    "Watch a status, and fire a post when status changes"

    @abstractmethod
    async def get_status(self, target: Target) -> Any:
        ...

    @abstractmethod
    def compare_status(self, target: Target, old_status, new_status) -> list[RawPost]:
        ...

    @abstractmethod
    async def parse(self, raw_post: RawPost) -> Post:
        ...

    async def fetch_new_post(
        self, target: Target, users: list[UserSubInfo]
    ) -> list[tuple[User, list[Post]]]:
        try:
            new_status = await self.get_status(target)
            res = []
            if old_status := self.get_stored_data(target):
                diff = self.compare_status(target, old_status, new_status)
                if diff:
                    logger.info(
                        "status changes {} {}: {} -> {}".format(
                            self.platform_name,
                            target if self.has_target else "-",
                            old_status,
                            new_status,
                        )
                    )
                    res = await self.dispatch_user_post(target, diff, users)
            self.set_stored_data(target, new_status)
            return res
        except httpx.RequestError as err:
            logger.warning(
                "network connection error: {}, url: {}".format(
                    type(err), err.request.url
                )
            )
            return []


class SimplePost(MessageProcess, abstract=True):
    "Fetch a list of messages, dispatch it to different users"

    async def fetch_new_post(
        self, target: Target, users: list[UserSubInfo]
    ) -> list[tuple[User, list[Post]]]:
        try:
            new_posts = await self.get_sub_list(target)
            if not new_posts:
                return []
            else:
                for post in new_posts:
                    logger.info(
                        "fetch new post from {} {}: {}".format(
                            self.platform_name,
                            target if self.has_target else "-",
                            self.get_id(post),
                        )
                    )
            res = await self.dispatch_user_post(target, new_posts, users)
            self.parse_cache = {}
            return res
        except httpx.RequestError as err:
            logger.warning(
                "network connection error: {}, url: {}".format(
                    type(err), err.request.url
                )
            )
            return []


class NoTargetGroup(Platform, abstract=True):
    enable_tag = False
    DUMMY_STR = "_DUMMY"
    enabled = True
    has_target = False

    def __init__(self, platform_list: list[Platform]):
        self.platform_list = platform_list
        name = self.DUMMY_STR
        self.categories = {}
        categories_keys = set()
        self.schedule_type = platform_list[0].schedule_type
        self.schedule_kw = platform_list[0].schedule_kw
        for platform in platform_list:
            if platform.has_target:
                raise RuntimeError(
                    "Platform {} should have no target".format(platform.name)
                )
            if name == self.DUMMY_STR:
                name = platform.name
            elif name != platform.name:
                raise RuntimeError(
                    "Platform name for {} not fit".format(self.platform_name)
                )
            platform_category_key_set = set(platform.categories.keys())
            if platform_category_key_set & categories_keys:
                raise RuntimeError(
                    "Platform categories for {} duplicate".format(self.platform_name)
                )
            categories_keys |= platform_category_key_set
            self.categories.update(platform.categories)
            if (
                platform.schedule_kw != self.schedule_kw
                or platform.schedule_type != self.schedule_type
            ):
                raise RuntimeError(
                    "Platform scheduler for {} not fit".format(self.platform_name)
                )
        self.name = name
        self.is_common = platform_list[0].is_common
        super().__init__()

    def __str__(self):
        return "[" + " ".join(map(lambda x: x.name, self.platform_list)) + "]"

    async def get_target_name(self, _):
        return await self.platform_list[0].get_target_name(_)

    async def fetch_new_post(self, target, users):
        res = defaultdict(list)
        for platform in self.platform_list:
            platform_res = await platform.fetch_new_post(target=target, users=users)
            for user, posts in platform_res:
                res[user].extend(posts)
        return [[key, val] for key, val in res.items()]
