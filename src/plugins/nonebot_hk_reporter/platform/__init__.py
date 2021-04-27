from .platform import PlatformProto
from pkgutil import iter_modules
from pathlib import Path
from importlib import import_module

_package_dir = str(Path(__file__).resolve().parent)
for (_, module_name, _) in iter_modules([_package_dir]):
    import_module(f'{__name__}.{module_name}')


async def check_sub_target(target_type, target):
    return await platform_manager[target_type].get_account_name(target)

platform_manager: dict[str, PlatformProto] = {
        obj.platform_name: obj() for obj in \
                filter(lambda platform: platform.enabled, PlatformProto.registory)
    }
