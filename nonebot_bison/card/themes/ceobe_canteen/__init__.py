from .stem import Card as CeobeStem
from ...registry import ThemeMetadata

__theme_meta__ = ThemeMetadata(
    theme=CeobeStem.get_theme_name(),
    stem=CeobeStem,
)
