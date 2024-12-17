from collections import defaultdict
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from nonebot_bison.plugin_config import plugin_config

from .platform import Platform, make_no_target_group

_package_dir = str(Path(__file__).resolve().parent)
for _, module_name, _ in iter_modules([_package_dir]):
    import_module(f"{__name__}.{module_name}")


_platform_list: defaultdict[str, list[type[Platform]]] = defaultdict(list)
for _platform in Platform.registry:
    if not _platform.enabled:
        continue
    _platform_list[_platform.platform_name].append(_platform)

platform_manager: dict[str, type[Platform]] = {}
for name, platform_list in _platform_list.items():
    if len(platform_list) == 1:
        platform_manager[name] = platform_list[0]
    else:
        platform_manager[name] = make_no_target_group(platform_list)


def _get_unavailable_platforms() -> dict[str, str]:
    res = {}
    for name, platform in platform_manager.items():
        if platform.site.require_browser and not plugin_config.bison_use_browser:
            res[name] = "需要启用 bison_use_browser"
    return res


# platform => reason for not available
unavailable_paltforms: dict[str, str] = _get_unavailable_platforms()
