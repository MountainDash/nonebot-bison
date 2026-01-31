from typing_extensions import TypeIs

from nonebot_bison.core.schedule import SubUnits

from .config import PlatformConfig as PlatformConfig
from .platform import BatchFetchMixin as BatchFetchMixin
from .platform import CategoryException as CategoryException
from .platform import CategoryNotRecognize as CategoryNotRecognize
from .platform import CategoryNotSupported as CategoryNotSupported
from .platform import FetchMixin as FetchMixin
from .platform import FilterMixin as FilterMixin
from .platform import Platform as Platform
from .platform import TargetedPosts as TargetedPosts


class CompletedFetchPlatform(Platform, FetchMixin, FilterMixin, abstract=True): ...


class CompletedBatchFetchPlatform(Platform, BatchFetchMixin, FilterMixin, abstract=True): ...


type CompletedPlatform = CompletedBatchFetchPlatform | CompletedFetchPlatform

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

def fetch_new_post(platform: CompletedPlatform, sub_unit: SubUnits) -> TargetedPosts:
    pass
