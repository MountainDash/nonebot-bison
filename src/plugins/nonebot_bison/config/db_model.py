import datetime
from pathlib import Path
from typing import Optional

from nonebot_plugin_datastore import get_plugin_data
from sqlmodel import JSON, Column, Field, Relationship, UniqueConstraint

from ..types import Category, Tag

Model = get_plugin_data().Model
get_plugin_data().set_migration_dir(Path(__file__).parent / "migrations")


class User(Model, table=True):
    __table_args__ = (UniqueConstraint("type", "uid", name="unique-user-constraint"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(max_length=20)
    uid: int

    subscribes: list["Subscribe"] = Relationship(back_populates="user")


class Target(Model, table=True):
    __table_args__ = (
        UniqueConstraint("target", "platform_name", name="unique-target-constraint"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    platform_name: str = Field(max_length=20)
    target: str = Field(max_length=1024)
    target_name: str = Field(max_length=1024)
    default_schedule_weight: Optional[int] = Field(default=10)

    subscribes: list["Subscribe"] = Relationship(back_populates="target")
    time_weight: list["ScheduleTimeWeight"] = Relationship(back_populates="target")


class ScheduleTimeWeight(Model, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: Optional[int] = Field(
        default=None, foreign_key="nonebot_bison_target.id"
    )
    start_time: Optional[datetime.time]
    end_time: Optional[datetime.time]
    weight: Optional[int]

    target: Target = Relationship(back_populates="time_weight")

    class Config:
        arbitrary_types_allowed = True


class Subscribe(Model, table=True):
    __table_args__ = (
        UniqueConstraint("target_id", "user_id", name="unique-subscribe-constraint"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: Optional[int] = Field(
        default=None, foreign_key="nonebot_bison_target.id"
    )
    user_id: Optional[int] = Field(default=None, foreign_key="nonebot_bison_user.id")
    categories: list[Category] = Field(sa_column=Column(JSON))
    tags: list[Tag] = Field(sa_column=Column(JSON))

    target: Target = Relationship(back_populates="subscribes")
    user: User = Relationship(back_populates="subscribes")
