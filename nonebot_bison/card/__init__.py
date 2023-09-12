from pathlib import Path
from pkgutil import iter_modules
from importlib import import_module

from nonebot.log import logger

from .types import BaseStem as BaseStem
from .registry import card_manager as card_manager
from .registry import ThemeMetadata as ThemeMetadata

_themes_dir = str((Path(__file__).parent / "themes").resolve())

for _, theme, _ in iter_modules([_themes_dir]):
    theme_module = import_module(f"{__name__}.themes.{theme}")
    if hasattr(theme_module, "__theme_meta__"):
        if isinstance(theme_module.__theme_meta__, ThemeMetadata):
            card_manager.register(theme_module.__theme_meta__)
        else:
            logger.error("Theme metadata is not a ThemeMetadata instance")
            raise TypeError("Theme metadata is not a ThemeMetadata instance")
    else:
        logger.warning(f"Theme {theme} has no __theme_meta__, ignored")
