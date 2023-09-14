from .stem import Card as ArkStem
from ...registry import ThemeMetadata

__theme_meta__ = ThemeMetadata(
    theme=ArkStem.get_theme_name(),
    stem=ArkStem,
)
