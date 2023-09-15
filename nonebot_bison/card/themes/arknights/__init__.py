from .stem import Stem
from ...registry import ThemeMetadata

__theme_meta__ = ThemeMetadata(
    theme=Stem.get_theme_name(),
    stem=Stem,
)
