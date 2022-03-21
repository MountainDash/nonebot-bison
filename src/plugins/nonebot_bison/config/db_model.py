from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import Integer, String

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)
    uid = Column(Integer, nullable=False)


class Target(Base):
    __tablename__ = "target"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_name = Column(String(20), nullable=False)
    target = Column(String(1024), nullable=False)
    target_name = Column(String(1024), nullable=False)


class Subscribe(Base):
    __tablename__ = "subscribe"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(Integer, ForeignKey(Target.id))
    user_id = Column(Integer, ForeignKey(User.id))
    categories = Column(String(1024))
    tags = Column(String(1024))

    target = relationship("Target")
    user = relationship("User")
