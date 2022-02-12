from collections import defaultdict
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from .platform import NoTargetGroup, Platform

_package_dir = str(Path(__file__).resolve().parent)
for (_, module_name, _) in iter_modules([_package_dir]):
    import_module(f"{__name__}.{module_name}")


async def check_sub_target(target_type, target):
    return await platform_manager[target_type].get_target_name(target)


_platform_list = defaultdict(list)
for _platform in Platform.registry:
    if not _platform.enabled:
        continue
    _platform_list[_platform.platform_name].append(_platform)

platform_manager: dict[str, Platform] = dict()
for name, platform_list in _platform_list.items():
    if len(platform_list) == 1:
        platform_manager[name] = platform_list[0]()
    else:
        platform_manager[name] = NoTargetGroup(
            [_platform() for _platform in platform_list]
        )
