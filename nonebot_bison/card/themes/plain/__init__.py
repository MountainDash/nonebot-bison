from ...types import ThemeMetadata
from .stem import Stem as PlainStem

__theme_meta__ = ThemeMetadata(
    theme=PlainStem.get_theme_name(),
    stem=PlainStem,
)
