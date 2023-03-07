""" nbexf is Nonebot Bison Enchangable Subscribes File! """

from dataclasses import dataclass

from ..types import Category, Tag


@dataclass
class ItemModel:
    user: int
    user_type: str
    target: str
    target_name: str
    platform_name: str
    categories: list[Category]
    tags: list[Tag]
    # default_schedule_weight: int
