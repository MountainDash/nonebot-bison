import ssl
import json
import time
import typing
from dataclasses import dataclass
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, TypeVar, ParamSpec
from collections.abc import Callable, Awaitable, Collection

import httpx
from httpx import AsyncClient
from nonebot.log import logger
from nonebot_plugin_saa import PlatformTarget

from ..post import Post
from ..plugin_config import plugin_config
from ..utils import ProcessContext, SchedulerConfig
from ..types import Tag, Target, RawPost, SubUnit, Category


class CategoryNotSupport(Exception):
    """raise in get_category, when you know the category of the post
    but don't want to support it or don't support its parsing yet
    """


class CategoryNotRecognize(Exception):
    """raise in get_category, when you don't know the category of post"""


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


P = ParamSpec("P")
R = TypeVar("R")


async def catch_network_error(func: Callable[P, Awaitable[R]], *args: P.args, **kwargs: P.kwargs) -> R | None:
    try:
        return await func(*args, **kwargs)
    except httpx.RequestError as err:
        if plugin_config.bison_show_network_warning:
            logger.warning(f"network connection error: {type(err)}, url: {err.request.url}")
        return None
    except ssl.SSLError as err:
        if plugin_config.bison_show_network_warning:
            logger.warning(f"ssl error: {err}")
        return None
    except json.JSONDecodeError as err:
        logger.warning(f"json error, parsing: {err.doc}")
        raise err


class PlatformMeta(RegistryMeta):
    categories: dict[Category, str]
    store: dict[Target, Any]

    def __init__(cls, name, bases, namespace, **kwargs):
        cls.reverse_category = {}
        cls.store = {}
        if hasattr(cls, "categories") and cls.categories:
            for key, val in cls.categories.items():
                cls.reverse_category[val] = key
        super().__init__(name, bases, namespace, **kwargs)


class PlatformABCMeta(PlatformMeta, ABC): ...


class Platform(metaclass=PlatformABCMeta, base=True):
    scheduler: type[SchedulerConfig]
    ctx: ProcessContext
    is_common: bool
    enabled: bool
    name: str
    has_target: bool
    categories: dict[Category, str]
    enable_tag: bool
    platform_name: str
    parse_target_promot: str | None = None
    registry: list[type["Platform"]]
    client: AsyncClient
    reverse_category: dict[str, Category]
    use_batch: bool = False
    # TODO: 限定可使用的theme名称
    default_theme: str = "basic"

    @classmethod
    @abstractmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None: ...

    @abstractmethod
    async def fetch_new_post(self, sub_unit: SubUnit) -> list[tuple[PlatformTarget, list[Post]]]: ...

    async def do_fetch_new_post(self, sub_unit: SubUnit) -> list[tuple[PlatformTarget, list[Post]]]:
        return await catch_network_error(self.fetch_new_post, sub_unit) or []

    @abstractmethod
    async def batch_fetch_new_post(self, sub_units: list[SubUnit]) -> list[tuple[PlatformTarget, list[Post]]]: ...

    async def do_batch_fetch_new_post(self, sub_units: list[SubUnit]) -> list[tuple[PlatformTarget, list[Post]]]:
        return await catch_network_error(self.batch_fetch_new_post, sub_units) or []

    @abstractmethod
    async def parse(self, raw_post: RawPost) -> Post: ...

    async def do_parse(self, raw_post: RawPost) -> Post:
        "actually function called"
        return await self.parse(raw_post)

    def __init__(self, context: ProcessContext, client: AsyncClient):
        super().__init__()
        self.client = client
        self.ctx = context

    class ParseTargetException(Exception):
        pass

    @classmethod
    async def parse_target(cls, target_string: str) -> Target:
        return Target(target_string)

    @abstractmethod
    def get_tags(self, raw_post: RawPost) -> Collection[Tag] | None:
        "Return Tag list of given RawPost"

    @classmethod
    def get_stored_data(cls, target: Target) -> Any:
        return cls.store.get(target)

    @classmethod
    def set_stored_data(cls, target: Target, data: Any):
        cls.store[target] = data

    def tag_separator(self, stored_tags: list[Tag]) -> tuple[list[Tag], list[Tag]]:
        """返回分离好的正反tag元组"""
        subscribed_tags = []
        banned_tags = []
        for tag in stored_tags:
            if tag.startswith("~"):
                banned_tags.append(tag.lstrip("~"))
            else:
                subscribed_tags.append(tag)
        return subscribed_tags, banned_tags

    def is_banned_post(
        self,
        post_tags: Collection[Tag],
        subscribed_tags: list[Tag],
        banned_tags: list[Tag],
    ) -> bool:
        """只要存在任意屏蔽tag则返回真，此行为优先级最高。
        存在任意被订阅tag则返回假，此行为优先级次之。
        若被订阅tag为空，则返回假。
        """
        # 存在任意需要屏蔽的tag则为真
        if banned_tags:
            for tag in post_tags or []:
                if tag in banned_tags:
                    return True
        # 检测屏蔽tag后，再检测订阅tag
        # 存在任意需要订阅的tag则为假
        if subscribed_tags:
            ban_it = True
            for tag in post_tags or []:
                if tag in subscribed_tags:
                    ban_it = False
            return ban_it
        else:
            return False

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
                raw_post_tags = self.get_tags(raw_post)
                if isinstance(raw_post_tags, Collection) and self.is_banned_post(
                    raw_post_tags, *self.tag_separator(tags)
                ):
                    continue
            res.append(raw_post)
        return res

    async def dispatch_user_post(
        self, new_posts: list[RawPost], sub_unit: SubUnit
    ) -> list[tuple[PlatformTarget, list[Post]]]:
        res: list[tuple[PlatformTarget, list[Post]]] = []
        for user, cats, required_tags in sub_unit.user_sub_infos:
            user_raw_post = await self.filter_user_custom(new_posts, cats, required_tags)
            user_post: list[Post] = []
            for raw_post in user_raw_post:
                user_post.append(await self.do_parse(raw_post))
            res.append((user, user_post))
        return res

    @abstractmethod
    def get_category(self, post: RawPost) -> Category | None:
        "Return category of given Rawpost"
        raise NotImplementedError()


class MessageProcess(Platform, abstract=True):
    "General message process fetch, parse, filter progress"

    def __init__(self, ctx: ProcessContext, client: AsyncClient):
        super().__init__(ctx, client)
        self.parse_cache: dict[Any, Post] = {}

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
        raise NotImplementedError()

    @abstractmethod
    async def batch_get_sub_list(self, targets: list[Target]) -> list[list[RawPost]]:
        "Get post list of the given targets"
        raise NotImplementedError()

    @abstractmethod
    def get_date(self, post: RawPost) -> int | None:
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
            except CategoryNotSupport as e:
                logger.info("未支持解析的推文类别：" + repr(e) + "，忽略")
                continue
            except CategoryNotRecognize as e:
                logger.warning("未知推文类别：" + repr(e))
                msgs = self.ctx.gen_req_records()
                for m in msgs:
                    logger.warning(m)
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

    async def filter_common_with_diff(self, target: Target, raw_post_list: list[RawPost]) -> list[RawPost]:
        filtered_post = await self.filter_common(raw_post_list)
        store = self.get_stored_data(target) or self.MessageStorage(False, set())
        res = []
        if not store.inited and plugin_config.bison_init_filter:
            # target not init
            for raw_post in filtered_post:
                post_id = self.get_id(raw_post)
                store.exists_posts.add(post_id)
            logger.info(f"init {self.platform_name}-{target} with {store.exists_posts}")
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

    async def _handle_new_post(
        self,
        post_list: list[RawPost],
        sub_unit: SubUnit,
    ) -> list[tuple[PlatformTarget, list[Post]]]:
        new_posts = await self.filter_common_with_diff(sub_unit.sub_target, post_list)
        if not new_posts:
            return []
        else:
            for post in new_posts:
                logger.info(
                    "fetch new post from {} {}: {}".format(
                        self.platform_name,
                        sub_unit.sub_target if self.has_target else "-",
                        self.get_id(post),
                    )
                )
        res = await self.dispatch_user_post(new_posts, sub_unit)
        self.parse_cache = {}
        return res

    async def fetch_new_post(self, sub_unit: SubUnit) -> list[tuple[PlatformTarget, list[Post]]]:
        post_list = await self.get_sub_list(sub_unit.sub_target)
        return await self._handle_new_post(post_list, sub_unit)

    async def batch_fetch_new_post(self, sub_units: list[SubUnit]) -> list[tuple[PlatformTarget, list[Post]]]:
        if not self.has_target:
            raise RuntimeError("Target without target should not use batch api")  # pragma: no cover
        posts_set = await self.batch_get_sub_list([x[0] for x in sub_units])
        res = []
        for sub_unit, posts in zip(sub_units, posts_set):
            res.extend(await self._handle_new_post(posts, sub_unit))
        return res


class StatusChange(Platform, abstract=True):
    "Watch a status, and fire a post when status changes"

    class FetchError(RuntimeError):
        pass

    @abstractmethod
    async def get_status(self, target: Target) -> Any: ...

    @abstractmethod
    async def batch_get_status(self, targets: list[Target]) -> list[Any]: ...

    @abstractmethod
    def compare_status(self, target: Target, old_status, new_status) -> list[RawPost]: ...

    @abstractmethod
    async def parse(self, raw_post: RawPost) -> Post: ...

    async def _handle_status_change(
        self, new_status: Any, sub_unit: SubUnit
    ) -> list[tuple[PlatformTarget, list[Post]]]:
        res = []
        if old_status := self.get_stored_data(sub_unit.sub_target):
            diff = self.compare_status(sub_unit.sub_target, old_status, new_status)
            if diff:
                logger.info(
                    "status changes {} {}: {} -> {}".format(
                        self.platform_name,
                        sub_unit.sub_target if self.has_target else "-",
                        old_status,
                        new_status,
                    )
                )
                res = await self.dispatch_user_post(diff, sub_unit)
        self.set_stored_data(sub_unit.sub_target, new_status)
        return res

    async def fetch_new_post(self, sub_unit: SubUnit) -> list[tuple[PlatformTarget, list[Post]]]:
        try:
            new_status = await self.get_status(sub_unit.sub_target)
        except self.FetchError as err:
            logger.warning(f"fetching {self.name}-{sub_unit.sub_target} error: {err}")
            raise
        return await self._handle_status_change(new_status, sub_unit)

    async def batch_fetch_new_post(self, sub_units: list[SubUnit]) -> list[tuple[PlatformTarget, list[Post]]]:
        if not self.has_target:
            raise RuntimeError("Target without target should not use batch api")  # pragma: no cover
        new_statuses = await self.batch_get_status([x[0] for x in sub_units])
        res = []
        for sub_unit, new_status in zip(sub_units, new_statuses):
            res.extend(await self._handle_status_change(new_status, sub_unit))
        return res


class SimplePost(NewMessage, abstract=True):
    "Fetch a list of messages, dispatch it to different users"

    async def _handle_new_post(
        self,
        new_posts: list[RawPost],
        sub_unit: SubUnit,
    ) -> list[tuple[PlatformTarget, list[Post]]]:
        if not new_posts:
            return []
        else:
            for post in new_posts:
                logger.info(
                    "fetch new post from {} {}: {}".format(
                        self.platform_name,
                        sub_unit.sub_target if self.has_target else "-",
                        self.get_id(post),
                    )
                )
        res = await self.dispatch_user_post(new_posts, sub_unit)
        self.parse_cache = {}
        return res


def make_no_target_group(platform_list: list[type[Platform]]) -> type[Platform]:
    if typing.TYPE_CHECKING:

        class NoTargetGroup(Platform, abstract=True):
            platform_list: list[type[Platform]]
            platform_obj_list: list[Platform]

    DUMMY_STR = "_DUMMY"

    platform_name = platform_list[0].platform_name
    name = DUMMY_STR
    categories_keys = set()
    categories = {}
    scheduler = platform_list[0].scheduler

    for platform in platform_list:
        if platform.has_target:
            raise RuntimeError(f"Platform {platform.name} should have no target")
        if name == DUMMY_STR:
            name = platform.name
        elif name != platform.name:
            raise RuntimeError(f"Platform name for {platform_name} not fit")
        platform_category_key_set = set(platform.categories.keys())
        if platform_category_key_set & categories_keys:
            raise RuntimeError(f"Platform categories for {platform_name} duplicate")
        categories_keys |= platform_category_key_set
        categories.update(platform.categories)
        if platform.scheduler != scheduler:
            raise RuntimeError(f"Platform scheduler for {platform_name} not fit")

    def __init__(self: "NoTargetGroup", ctx: ProcessContext, client: AsyncClient):
        Platform.__init__(self, ctx, client)
        self.platform_obj_list = []
        for platform_class in self.platform_list:
            self.platform_obj_list.append(platform_class(ctx, client))

    def __str__(self: "NoTargetGroup") -> str:
        return "[" + " ".join(x.name for x in self.platform_list) + "]"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target):
        return await platform_list[0].get_target_name(client, target)

    async def fetch_new_post(self: "NoTargetGroup", sub_unit: SubUnit):
        res = defaultdict(list)
        for platform in self.platform_obj_list:
            platform_res = await platform.fetch_new_post(sub_unit)
            for user, posts in platform_res:
                res[user].extend(posts)
        return [[key, val] for key, val in res.items()]

    return type(
        "NoTargetGroup",
        (Platform,),
        {
            "platform_list": platform_list,
            "platform_name": platform_list[0].platform_name,
            "name": name,
            "categories": categories,
            "scheduler": scheduler,
            "is_common": platform_list[0].is_common,
            "enabled": True,
            "has_target": False,
            "enable_tag": False,
            "__init__": __init__,
            "get_target_name": get_target_name,
            "fetch_new_post": fetch_new_post,
        },
        abstract=True,
    )
