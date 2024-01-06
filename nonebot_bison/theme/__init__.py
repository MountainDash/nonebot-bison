from pathlib import Path
from pkgutil import iter_modules
from importlib import import_module

from .types import Theme
from .registry import theme_manager
from .schemas import Parcel as Parcel
from .types import ThemeRegistrationError
from .schemas import ParcelHeader as ParcelHeader
from .schemas import ParcelPayload as ParcelPayload
from .types import ThemeRenderError as ThemeRenderError
from .types import ThemeRenderUnsupportError as ThemeRenderUnsupportError

_theme_dir = str((Path(__file__).parent / "themes").resolve())

for _, theme, _ in iter_modules([_theme_dir]):
    theme_module = import_module(f"{__name__}.themes.{theme}")

    if not hasattr(theme_module, "__theme_meta__"):
        raise ThemeRegistrationError(f"{theme} has no __theme_meta__")

    if not isinstance(theme_module.__theme_meta__, Theme):
        raise ThemeRegistrationError(f"{theme}'s __theme_meta__ is not a AbstractTheme instance")

    theme_manager.register(theme_module.__theme_meta__)
