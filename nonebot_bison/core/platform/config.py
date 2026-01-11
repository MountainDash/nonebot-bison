from dataclasses import dataclass
from functools import cached_property

from nonebot_bison.typing import Category


@dataclass(frozen=True, kw_only=True)
class PlatformConfig:
    name: str
    """平台名称, 用于区分不同平台，是唯一标识"""
    is_common: bool = True
    """在添加订阅时是否折叠隐藏"""
    enable: bool = True
    """初始是否启用该平台"""
    has_target: bool
    """该平台是否存在账号目标"""
    enable_tag: bool = True
    """初始是否启用标签过滤功能"""
    display_name: str
    """平台向用户显示的名称"""
    parse_target_promot: str | None = None
    """解析平台账号时的提示语"""
    use_batch: bool = False
    """是否支持批量获取平台账号内容"""
    preferred_theme: str = "basic"
    """平台优先使用进行渲染的主题"""
    categories: dict[Category, str] | None = None
    """平台支持的分类列表，键为分类 ID，值为分类名称"""

    @cached_property
    def reverse_category(self):
        if self.categories is None:
            return {}
        return {v: k for k, v in self.categories.items()}
