from typing import Any, Callable, NamedTuple, NewType
from dataclasses import dataclass

RawPost = NewType('RawPost', Any)
Target = NewType('Target', str)
Category = NewType('Category', int)
Tag = NewType('Tag', str)

@dataclass(eq=True, frozen=True)
class User:
    user: str
    user_type: str

class UserSubInfo(NamedTuple):
    user: User
    category_getter: Callable[[Target], list[Category]]
    tag_getter: Callable[[Target], list[Tag]]
