from datetime import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.sql.sqltypes import JSON, DateTime, Integer, String

Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("type", "uid", name="unique-user-constraint"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)
    uid = Column(Integer, nullable=False)

    subscribes = relationship("Subscribe", back_populates="user")


class Target(Base):
    __tablename__ = "target"
    __table_args__ = (
        UniqueConstraint("target", "platform_name", name="unique-target-constraint"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_name = Column(String(20), nullable=False)
    target = Column(String(1024), nullable=False)
    target_name = Column(String(1024), nullable=False)
    last_schedule_time = Column(
        DateTime(timezone=True), default=datetime(year=2000, month=1, day=1)
    )

    subscribes = relationship("Subscribe", back_populates="target")


class Subscribe(Base):
    __tablename__ = "subscribe"
    __table_args__ = (
        UniqueConstraint("target_id", "user_id", name="unique-subscribe-constraint"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(Integer, ForeignKey(Target.id))
    user_id = Column(Integer, ForeignKey(User.id))
    categories = Column(JSON)
    tags = Column(JSON)

    target = relationship("Target", back_populates="subscribes")
    user = relationship("User", back_populates="subscribes")
