import datetime
from pathlib import Path

from nonebot_plugin_saa import PlatformTarget
from sqlalchemy.dialects.postgresql import JSONB
from nonebot.compat import PYDANTIC_V2, ConfigDict
from nonebot_plugin_datastore import get_plugin_data
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy import JSON, String, ForeignKey, UniqueConstraint

from ..types import Tag, Category

Model = get_plugin_data().Model
get_plugin_data().set_migration_dir(Path(__file__).parent / "migrations")


class User(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_target: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))

    subscribes: Mapped[list["Subscribe"]] = relationship(back_populates="user")

    @property
    def saa_target(self) -> PlatformTarget:
        return PlatformTarget.deserialize(self.user_target)


class Target(Model):
    __table_args__ = (UniqueConstraint("target", "platform_name", name="unique-target-constraint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_name: Mapped[str] = mapped_column(String(20))
    target: Mapped[str] = mapped_column(String(1024))
    target_name: Mapped[str] = mapped_column(String(1024))
    default_schedule_weight: Mapped[int] = mapped_column(default=10)

    subscribes: Mapped[list["Subscribe"]] = relationship(back_populates="target")
    time_weight: Mapped[list["ScheduleTimeWeight"]] = relationship(back_populates="target")


class ScheduleTimeWeight(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("nonebot_bison_target.id"))
    start_time: Mapped[datetime.time]
    end_time: Mapped[datetime.time]
    weight: Mapped[int]

    target: Mapped[Target] = relationship(back_populates="time_weight")

    if PYDANTIC_V2:
        model_config = ConfigDict(arbitrary_types_allowed=True)
    else:

        class Config:
            arbitrary_types_allowed = True


class Subscribe(Model):
    __table_args__ = (UniqueConstraint("target_id", "user_id", name="unique-subscribe-constraint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("nonebot_bison_target.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("nonebot_bison_user.id"))
    categories: Mapped[list[Category]] = mapped_column(JSON)
    tags: Mapped[list[Tag]] = mapped_column(JSON)

    target: Mapped[Target] = relationship(back_populates="subscribes")
    user: Mapped[User] = relationship(back_populates="subscribes")
