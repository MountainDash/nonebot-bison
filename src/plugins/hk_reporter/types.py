from typing import Any, NewType
from dataclasses import dataclass

RawPost = NewType('RawPost', Any)
Target = NewType('Target', str)
Category = NewType('Category', int)
Tag = NewType('Tag', str)

@dataclass
class User:
    user: str
    user_type: str
