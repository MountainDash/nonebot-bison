from nonebot_bison.core.platform import PlatformConfig
from nonebot_bison.setting import plugin_config


def get_config_theme(platform: PlatformConfig) -> str | None:
    """获取用户指定的theme"""
    return plugin_config.bison_platform_theme.get(platform.preferred_theme)

def get_priority_themes(platform: PlatformConfig) -> list[str]:
    """获取渲染所使用的theme名列表，按照优先级排序"""
    themes_by_priority: list[str] = []
    # 最先使用用户指定的theme
    if user_theme := get_config_theme(platform):
        themes_by_priority.append(user_theme)
    # 然后使用平台默认的theme
    if platform.preferred_theme not in themes_by_priority:
        themes_by_priority.append(platform.preferred_theme)
    # 最后使用最基础的theme
    if "basic" not in themes_by_priority:
        themes_by_priority.append("basic")
    return themes_by_priority
