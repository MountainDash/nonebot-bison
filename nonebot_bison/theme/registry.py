from nonebot import logger

from .types import AbstractTheme, ThemeRegistrationError


class ThemeManager:
    __themes: dict[str, AbstractTheme] = {}

    def register(self, theme: AbstractTheme):
        logger.trace(f"Registering theme: {theme}")
        if theme.name in self.__themes:
            raise ThemeRegistrationError(f"Theme {theme.name} duplicated registration")
        self.__themes[theme.name] = theme
        logger.opt(colors=True).success(f"Theme <b><u>{theme.name}</u></b> registered")

    def __getitem__(self, theme: str):
        return self.__themes[theme]

    def __len__(self):
        return len(self.__themes)

    def __contains__(self, theme: str):
        return theme in self.__themes


theme_manager = ThemeManager()
