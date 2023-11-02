from nonebot import logger

from ..plugin_config import plugin_config
from .types import Theme, ThemeRegistrationError


class ThemeManager:
    __themes: dict[str, Theme] = {}

    def register(self, theme: Theme):
        logger.trace(f"Registering theme: {theme}")
        if theme.name in self.__themes:
            raise ThemeRegistrationError(f"Theme {theme.name} duplicated registration")
        if theme.need_browser and not plugin_config.bison_theme_use_browser:
            logger.opt(colors=True).warning(f"Theme <b><u>{theme.name}</u></b> requires browser, but not allowed")
        self.__themes[theme.name] = theme
        logger.opt(colors=True).success(f"Theme <b><u>{theme.name}</u></b> registered")

    def unregister(self, theme_name: str):
        logger.trace(f"Unregistering theme: {theme_name}")
        if theme_name not in self.__themes:
            raise ThemeRegistrationError(f"Theme {theme_name} was not registered")
        self.__themes.pop(theme_name)
        logger.opt(colors=True).success(f"Theme <b><u>{theme_name}</u></b> unregistered")

    def __getitem__(self, theme: str):
        return self.__themes[theme]

    def __len__(self):
        return len(self.__themes)

    def __contains__(self, theme: str):
        return theme in self.__themes


theme_manager = ThemeManager()
