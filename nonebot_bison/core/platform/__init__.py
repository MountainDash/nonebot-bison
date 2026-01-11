from .config import PlatformConfig as PlatformConfig
from .platform import BatchFetchMixin as BatchFetchMixin
from .platform import FetchMixin as FetchMixin
from .platform import FilterMixin as FilterMixin
from .platform import Platform as Platform
from .platform import TargetedPosts as TargetedPosts


class CompletedFetchPlatform(Platform, FetchMixin, FilterMixin, abstract=True): ...


class CompletedBatchFetchPlatform(Platform, BatchFetchMixin, FilterMixin, abstract=True): ...


type CompletedPlatform = CompletedBatchFetchPlatform | CompletedFetchPlatform

def is_batch_platform(
    platform: CompletedPlatform,
) -> bool:
    """判断平台是否为批量获取平台"""
    return isinstance(platform, BatchFetchMixin)
