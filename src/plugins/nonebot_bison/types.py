from typing import Any, Callable, Literal, NamedTuple, NewType

from pydantic.dataclasses import dataclass

RawPost = NewType("RawPost", Any)
Target = NewType("Target", str)
Category = int
Tag = str


@dataclass(eq=True, frozen=True)
class User:
    user: int
    user_type: Literal["group", "private"]


class UserSubInfo(NamedTuple):
    user: User
    category_getter: Callable[[Target], list[Category]]
    tag_getter: Callable[[Target], list[Tag]]
