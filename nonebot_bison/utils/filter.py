from abc import abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import override

from nonebot import logger

from nonebot_bison.core.platform import CategoryNotRecognize, CategoryNotSupported, FilterMixin
from nonebot_bison.setting import plugin_config
from nonebot_bison.typing import Target
from nonebot_bison.utils.classproperty import classproperty


@dataclass
class _PostIDStorage:
    inited: bool = False
    stored_post_ids: set[str] = field(default_factory=set)

    def add(self, post_id: str) -> None:
        self.stored_post_ids.add(post_id)


class NewMessageFilter[RawPost](FilterMixin):
    TOO_OLD_THRESHOLD = timedelta(hours=2).total_seconds()

    @classproperty
    @classmethod
    def PostIDStorage(cls):
        return _PostIDStorage

    @override
    async def filter(
        self, target: Target, raw_posts: Iterable[RawPost]
    ) -> tuple[RawPost, ...]:
        filtered_posts: list[RawPost] = []

        for raw_post in raw_posts:
            if not self._is_fresh_post(raw_post):
                logger.trace(f"过滤过旧推文: {self.get_id(raw_post)}")
                continue
            if not self._is_valid_category(raw_post):
                continue
            if self._is_duplicate_post(target, raw_post):
                logger.trace(f"过滤重复推文: {self.get_id(raw_post)}")
                continue

            filtered_posts.append(raw_post)

        if self.record_on_startup(target, filtered_posts):
            return ()

        self.record_target_posts(target, filtered_posts)
        return tuple(filtered_posts)

    @abstractmethod
    def get_id(self, raw_post: RawPost) -> str: ...

    @abstractmethod
    def get_release_timestamp(self, raw_post: RawPost) -> int: ...

    def target_post_key(self, target: Target) -> str:
        return f"filter_recorded_posts::{self.name}::{target!s}"

    def get_target_post_store(self, target: Target):
        target_post_key = self.target_post_key(target)
        target_meesage_store = self.ctx.get_stored_data(target_post_key)
        if target_meesage_store is None:
            target_meesage_store = self.PostIDStorage()
            self.ctx.set_stored_data(target_post_key, target_meesage_store)

        return target_meesage_store

    def record_on_startup(
        self, target: Target, filtered_posts: Iterable[RawPost]
    ) -> bool:
        """记录启动时的推文, 返回 True 表示已记录推文且无需再处理这些推文， False 表示未启用启动记录配置"""
        post_id_store = self.get_target_post_store(target)
        if not post_id_store.inited and plugin_config.bison_filter_on_init:
            for raw_post in filtered_posts:
                post_id = self.get_id(raw_post)
                post_id_store.add(post_id)
            post_id_store.inited = True
            logger.info(
                f"Platform[{self.name}]初始过滤已记录推文 {post_id_store.stored_post_ids} 条"
            )
            return True

        return False

    def record_target_posts(self, target: Target, raw_posts: Iterable[RawPost]) -> None:
        target_meesage_store = self.get_target_post_store(target)

        for raw_post in raw_posts:
            post_id = self.get_id(raw_post)
            target_meesage_store.add(post_id)

    def _is_fresh_post(self, raw_post: RawPost) -> bool:
        post_time = self.get_release_timestamp(raw_post)
        elapsed = datetime.now(UTC).timestamp() - post_time

        return (
            elapsed <= self.TOO_OLD_THRESHOLD
            if plugin_config.bison_filter_on_init
            else False
        )

    def _is_valid_category(self, raw_post: RawPost) -> bool:
        try:
            self.get_category(raw_post)
        except CategoryNotSupported as e:
            logger.info("未支持解析的推文类别：" + repr(e) + "，忽略")
            return False
        except CategoryNotRecognize as e:
            logger.warning("未知推文类别：" + repr(e))
            msgs = self.ctx.gen_req_records()
            for m in msgs:
                logger.warning(m)
            return False

        return True

    def _is_duplicate_post(self, target: Target, raw_post: RawPost) -> bool:
        target_post_key = self.target_post_key(target)
        target_meesage_store = self.ctx.get_stored_data(target_post_key)
        if target_meesage_store is None:
            return False

        post_id = self.get_id(raw_post)
        if post_id in target_meesage_store:
            target_meesage_store.add(post_id)
            return True

        return False
