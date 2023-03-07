""" nbexf is Nonebot Bison Enchangable Subscribes File! """

from dataclasses import dataclass
from typing import List

from pydantic import BaseModel

from ..types import Category, Tag


# use for export(pending)
class UserHead(BaseModel):
    type: str
    uid: int


class Target(BaseModel):
    target_name: str
    target: str
    platform_name: str
    default_schedule_weight: int


class SubPayload(BaseModel):
    categories: List
    tags: List
    target: Target


class SubPack(BaseModel):
    user: UserHead
    subs: List[SubPayload]


class SubGroup(BaseModel):
    __root__: List[SubPack]


# use for import
@dataclass
class ItemModel:
    user: int
    user_type: str
    target: str
    target_name: str
    platform_name: str
    cats: list[Category]
    tags: list[Tag]
    # default_schedule_weight: int
