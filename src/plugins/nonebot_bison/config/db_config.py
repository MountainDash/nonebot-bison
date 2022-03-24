import json
from typing import Optional

from nonebot_bison.types import Category, Tag, Target
from nonebot_plugin_datastore.db import create_session
from sqlalchemy.sql.expression import select

from .db_model import Subscribe as MSubscribe
from .db_model import Target as MTarget
from .db_model import User


class DBConfig:
    def __init__(self):
        self.session = create_session()

    async def add_subscribe(
        self,
        user: int,
        user_type: str,
        target: Target,
        target_name: str,
        platform_name: str,
        cats: list[Category],
        tags: list[Tag],
    ):
        db_user_stmt = (
            select(User).where(User.uid == user).where(User.type == user_type)
        )
        db_user: Optional[User] = (await self.session.scalars(db_user_stmt)).first()
        if not db_user:
            db_user = User(uid=user, type=user_type)
            self.session.add(db_user)
        db_target_stmt = (
            select(MTarget)
            .where(MTarget.platform_name == platform_name)
            .where(MTarget.target == target)
        )
        db_target: Optional[MTarget] = (
            await self.session.scalars(db_target_stmt)
        ).first()
        if not db_target:
            db_target = MTarget(
                target=target, platform_name=platform_name, target_name=target_name
            )
        else:
            db_target.target_name = target_name  # type: ignore
        subscribe = MSubscribe(
            categories=json.dumps(cats),
            tags=json.dumps(tags),
            user=db_user,
            target=db_target,
        )
        self.session.add(subscribe)
        await self.session.commit()


config = DBConfig()
