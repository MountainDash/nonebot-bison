from .schemas import Card
from ...registry import ThemeMetadata
from .render import card_render as card_render

__theme_meta__ = ThemeMetadata(
    theme="bison",
    render=card_render,
    schemas=Card,
)
