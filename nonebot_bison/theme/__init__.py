from pathlib import Path
from pkgutil import iter_modules
from importlib import import_module

from .types import AbstractTheme
from .registry import theme_manager
from .types import ThemeRegistrationError
from .types import ThemeRenderError as ThemeRenderError
from .types import ThemeRenderUnsupportError as ThemeRenderUnsupportError
from .utils import check_htmlrender_plugin_enable as check_htmlrender_plugin_enable

_theme_dir = str((Path(__file__).parent / "themes").resolve())

for _, theme, _ in iter_modules([_theme_dir]):
    theme_module = import_module(f"{__name__}.themes.{theme}")

    if not hasattr(theme_module, "__theme_meta__"):
        raise ThemeRegistrationError(f"{theme} has no __theme_meta__")

    if not isinstance(theme_module.__theme_meta__, AbstractTheme):
        raise ThemeRegistrationError(f"{theme}'s __theme_meta__ is not a AbstractTheme instance")

    theme_manager.register(theme_module.__theme_meta__)
