from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.sql.sqltypes import JSON, Integer, String, Time

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
    default_schedule_weight = Column(Integer, default=10)

    subscribes = relationship("Subscribe", back_populates="target")
    time_weight = relationship("ScheduleTimeWeight", back_populates="target")


class ScheduleTimeWeight(Base):
    __tablename__ = "schedule_time_weight"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(Integer, ForeignKey(Target.id))
    start_time = Column(Time)
    end_time = Column(Time)
    weight = Column(Integer)

    target = relationship("Target", back_populates="time_weight")


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
