from nonebot.log import logger

from .types import ThemeMetadata


class ThemeManager:
    _themes: dict[str, ThemeMetadata] = {}

    def register(self, card: ThemeMetadata):
        logger.trace(f"Registering card theme: {card}")
        if card.theme in self._themes:
            raise ValueError(f"Card theme {card.theme} already exists")
        self._themes[card.theme] = card
        logger.opt(colors=True).success(f"Registered card theme <b><u>{card.theme}</u></b>")

    def __getitem__(self, theme: str):
        return self._themes[theme]

    def __len__(self):
        return len(self._themes)

    def __contains__(self, theme: str):
        return theme in self._themes


theme_manager = ThemeManager()
