from nonebot.log import logger

from .types import ThemeMetadata


class CardManager:
    _cards: dict[str, ThemeMetadata] = {}

    def register(self, card: ThemeMetadata):
        logger.trace(f"Registering card {card}")
        if card.theme in self._cards:
            raise ValueError(f"Card {card.theme} already exists")
        logger.opt(colors=True).success(f"Registering card <b><u>{card.theme}</u></b>")
        self._cards[card.theme] = card

    def __getitem__(self, theme: str):
        return self._cards[theme]

    def __len__(self):
        return len(self._cards)

    def __contains__(self, theme: str):
        return theme in self._cards


card_manager = CardManager()
