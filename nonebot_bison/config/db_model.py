import datetime
from pathlib import Path
from typing import Any

from nonebot.compat import PYDANTIC_V2, ConfigDict
from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_saa import PlatformTarget
from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nonebot_bison.types import Category, Tag

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
    cookies: Mapped[list["CookieTarget"]] = relationship(back_populates="target")


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


class Cookie(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    site_name: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(String(1024))
    # Cookie 的友好名字，类似于 Target 的 target_name，用于展示
    cookie_name: Mapped[str] = mapped_column(String(1024), default="unnamed cookie")
    # 最后使用的时刻
    last_usage: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime(1970, 1, 1))
    # Cookie 当前的状态
    status: Mapped[str] = mapped_column(String(20), default="")
    # 使用一次之后，需要的冷却时间
    cd_milliseconds: Mapped[int] = mapped_column(default=0)
    # 是否是通用 Cookie（对所有Target都有效）
    is_universal: Mapped[bool] = mapped_column(default=False)
    # 是否是匿名 Cookie
    is_anonymous: Mapped[bool] = mapped_column(default=False)
    # 标签，扩展用
    tags: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default={})

    targets: Mapped[list["CookieTarget"]] = relationship(back_populates="cookie")

    @property
    def cd(self) -> datetime.timedelta:
        return datetime.timedelta(milliseconds=self.cd_milliseconds)

    @cd.setter
    def cd(self, value: datetime.timedelta):
        self.cd_milliseconds = int(value.total_seconds() * 1000)


class CookieTarget(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("nonebot_bison_target.id", ondelete="CASCADE"))
    cookie_id: Mapped[int] = mapped_column(ForeignKey("nonebot_bison_cookie.id", ondelete="CASCADE"))

    target: Mapped[Target] = relationship(back_populates="cookies")
    cookie: Mapped[Cookie] = relationship(back_populates="targets")
