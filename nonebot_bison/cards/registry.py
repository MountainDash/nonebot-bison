from io import BytesIO
from pathlib import Path
from collections.abc import Callable, Coroutine

from nonebot.log import logger
from pydantic import BaseModel


class ThemeMetadata(BaseModel):
    theme: str
    # FIXME: 这里想注解一个Callable[[BaseModel], Coroutine[None, None, bytes | BytesIO | Path | str]]
    # 但是在给render赋值一个接受BaseModel子类作为参数的函数时，Pylance会报错
    # 无法将类型“(card: Card) -> Coroutine[Any, Any, bytes]”分配给类型
    # “(BaseModel) -> Coroutine[None, None, bytes | BytesIO | Path | str]”
    # 参数 1: 无法将类型“BaseModel”分配给类型“Card”
    # “BaseModel”与“Card”不兼容
    # 现在临时变更为...，这样会导致无法检查render的参数类型
    render: Callable[..., Coroutine[None, None, bytes | BytesIO | Path | str]]
    schema: type[BaseModel]


class CardManager:
    _cards: dict[str, ThemeMetadata] = {}

    def register(self, card: ThemeMetadata):
        if card.theme in self._cards:
            raise ValueError(f"Card {card.theme} already exists")
        logger.opt(colors=True).success(f"Registering card <b><u>{card.theme}</u></b>")
        self._cards[card.theme] = card

    def get(self, theme: str):
        return self._cards[theme]


card_manager = CardManager()
