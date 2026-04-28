from typing import TYPE_CHECKING, Any, TypeIs

import anyio

from bison_core.typing import SubUnit, SubUnits
from bison_core.utils.registry import Registries, Registry

from .config import PlatformConfig as PlatformConfig
from .platform import BatchFetchMixin as BatchFetchMixin
from .platform import CategoryException as CategoryException
from .platform import CategoryNotRecognize as CategoryNotRecognize
from .platform import CategoryNotSupported as CategoryNotSupported
from .platform import FetchMixin as FetchMixin
from .platform import FilterMixin as FilterMixin
from .platform import Platform as Platform
from .platform import PlatformFetchMethodMismatch

if TYPE_CHECKING:
    from collections.abc import Sequence

    from nonebot_plugin_saa import PlatformTarget

    from bison_core.post import Post

type TargetedPosts = "Sequence[tuple[PlatformTarget, Sequence[Post]]]"


class CompletedFetchPlatform[RawPost](Platform[RawPost], FetchMixin[RawPost], FilterMixin[RawPost]): ...


class CompletedBatchFetchPlatform[RawPost](Platform[RawPost], BatchFetchMixin[RawPost], FilterMixin[RawPost]): ...


type CompletedPlatform[RawPost] = CompletedBatchFetchPlatform[RawPost] | CompletedFetchPlatform[RawPost]

platform: Registry[CompletedPlatform[Any]] = Registries.as_registry("platform")
"""平台注册器"""


@platform.as_checker
def check_platform_is_completed(cls: type[object]) -> bool:
    cls_bases = cls.__bases__
    need_bases = (Platform, FilterMixin)
    fetch_bases = (FetchMixin, BatchFetchMixin)
    has_need = all((nb in cls_bases) for nb in need_bases)
    has_fetch = any((fb in cls_bases) for fb in fetch_bases)
    return has_need and has_fetch


def is_batch_platform(
    platform: CompletedPlatform,
) -> TypeIs[CompletedBatchFetchPlatform]:
    """判断平台是否为批量获取平台"""
    if not isinstance(platform, BatchFetchMixin):
        return False

    mro = platform.__class__.__mro__

    def get_index(t: type):
        try:
            return mro.index(t)
        except ValueError:
            return len(mro)

    return get_index(BatchFetchMixin) < get_index(FetchMixin)

# QUESTION: 这个函数的实现一定要放 core 这里吗
async def fetch_new_post[RawPost](platform: CompletedPlatform[RawPost], sub_units: SubUnits) -> TargetedPosts:
    async def _do_fetch(unit: SubUnit):
        filtered_posts = await platform.filter(unit.sub_target, posts)
        for user, cats, tags in unit.user_sub_infos:
            dispatched_posts = await platform.dispatch(filtered_posts, cats, tags)
            parsed_posts: list[Post] = []

            async with anyio.create_task_group() as tg:
                for dp in dispatched_posts:

                    async def _do_parse():
                        p = await platform.parse(dp)
                        parsed_posts.append(p)

                    tg.start_soon(_do_parse)

            yield user, parsed_posts

    res: TargetedPosts = []
    match sub_units:
        case list(items) if is_batch_platform(platform):
            posts = await platform.fetch(items)

            for su in sub_units:
                async for p in _do_fetch(su):
                    res.append(p)

        case SubUnit() as item if not is_batch_platform(platform):
            posts = await platform.fetch(item)

            async for p in _do_fetch(item):
                res.append(p)

        case _:
            raise PlatformFetchMethodMismatch(
                f"platform `{platform.name}` is {'' if is_batch_platform(platform) else 'not'} batchable fetch,"
                f" but pass {'' if isinstance(sub_units, list) else 'not'} list value as `sub_units` argument."
            )

    return res
