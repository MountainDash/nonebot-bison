from nonebot import logger

from bison_core.utils.registry import Registries, Registry

from .theme import Theme

theme: Registry[Theme] = Registries.as_registry("theme")

@theme.as_checker
def check_theme(cls: type[Theme]) -> bool:
    return issubclass(cls, Theme) and cls.is_support_register()

@theme.on_post_register
def register_theme(cls: type[Theme]):
    logger.opt(colors=True).success(f"Registering theme <b><u>{cls.name}</u></b> successfully.")
