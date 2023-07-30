from pathlib import Path
from pkgutil import iter_modules
from importlib import import_module

from nonebot.log import logger

from .registry import card_manager as card_manager
from .registry import ThemeMetadata as ThemeMetadata

_themes_dir = str((Path(__file__).parent / "themes").resolve())

for _, card, _ in iter_modules([_themes_dir]):
    card_theme = import_module(f"{__name__}.themes.{card}")
    if hasattr(card_theme, "__theme_meta__"):
        if isinstance(card_theme.__theme_meta__, ThemeMetadata):
            card_manager.register(card_theme.__theme_meta__)
        else:
            logger.error("Theme metadata is not a ThemeMetadata instance")
            raise TypeError("Theme metadata is not a ThemeMetadata instance")
    else:
        logger.warning(f"Card {card} has no __theme_meta__, ignored")
