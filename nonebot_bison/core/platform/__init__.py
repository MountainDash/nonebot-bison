from typing_extensions import TypeIs

from nonebot_bison.core.schedule import SubUnit, SubUnits

from .config import PlatformConfig as PlatformConfig
from .platform import BatchFetchMixin as BatchFetchMixin
from .platform import CategoryException as CategoryException
from .platform import CategoryNotRecognize as CategoryNotRecognize
from .platform import CategoryNotSupported as CategoryNotSupported
from .platform import FetchMixin as FetchMixin
from .platform import FilterMixin as FilterMixin
from .platform import Platform as Platform
from .platform import PlatformFetchMethodMismatch
from .platform import TargetedPosts as TargetedPosts


class CompletedFetchPlatform[RawPost](Platform[RawPost], FetchMixin[RawPost], FilterMixin[RawPost], abstract=True): ...


class CompletedBatchFetchPlatform[RawPost](
    Platform[RawPost], BatchFetchMixin[RawPost], FilterMixin[RawPost], abstract=True
): ...


type CompletedPlatform[RawPost] = CompletedBatchFetchPlatform[RawPost] | CompletedFetchPlatform[RawPost]


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


async def fetch_new_post[RawPost](platform: CompletedPlatform[RawPost], sub_units: SubUnits) -> TargetedPosts:

    async def _do_fetch(unit: SubUnit):
        filtered_posts = await platform.filter(unit.sub_target, posts)
        for user, cats, tags in unit.user_sub_infos:
            dispatched_posts = await platform.dispatch(filtered_posts, cats, tags)
            parsed_posts = tuple(platform.parse(raw_post) for raw_post in dispatched_posts)
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
