from .schemas import Card
from .render import card_render as card_render
from ...registry import ThemeMetadata, card_manager

card_manager.register(
    ThemeMetadata(
        theme="bison",
        render=card_render,
        schema=Card,
    )
)
