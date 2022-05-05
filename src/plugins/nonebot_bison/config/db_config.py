from typing import Optional

from nonebot_bison.types import Category, Tag, Target
from nonebot_plugin_datastore.db import get_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.expression import delete, select
from sqlalchemy.sql.functions import func

from .db_model import Subscribe as MSubscribe
from .db_model import Target as MTarget
from .db_model import User


class DBConfig:
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
        async with AsyncSession(get_engine()) as session:
            db_user_stmt = (
                select(User).where(User.uid == user).where(User.type == user_type)
            )
            db_user: Optional[User] = await session.scalar(db_user_stmt)
            if not db_user:
                db_user = User(uid=user, type=user_type)
                session.add(db_user)
            db_target_stmt = (
                select(MTarget)
                .where(MTarget.platform_name == platform_name)
                .where(MTarget.target == target)
            )
            db_target: Optional[MTarget] = await session.scalar(db_target_stmt)
            if not db_target:
                db_target = MTarget(
                    target=target, platform_name=platform_name, target_name=target_name
                )
            else:
                db_target.target_name = target_name  # type: ignore
            subscribe = MSubscribe(
                categories=cats,
                tags=tags,
                user=db_user,
                target=db_target,
            )
            session.add(subscribe)
            await session.commit()

    async def list_subscribe(self, user: int, user_type: str) -> list[MSubscribe]:
        async with AsyncSession(get_engine()) as session:
            query_stmt = (
                select(MSubscribe)
                .where(User.type == user_type, User.uid == user)
                .join(User)
                .options(selectinload(MSubscribe.target))  # type:ignore
            )
            subs: list[MSubscribe] = (await session.scalars(query_stmt)).all()
            return subs

    async def del_subscribe(
        self, user: int, user_type: str, target: str, platform_name: str
    ):
        async with AsyncSession(get_engine()) as session:
            user_obj = await session.scalar(
                select(User).where(User.uid == user, User.type == user_type)
            )
            target_obj = await session.scalar(
                select(MTarget).where(
                    MTarget.platform_name == platform_name, MTarget.target == target
                )
            )
            await session.execute(
                delete(MSubscribe).where(
                    MSubscribe.user == user_obj, MSubscribe.target == target_obj
                )
            )
            target_count = await session.scalar(
                select(func.count())
                .select_from(MSubscribe)
                .where(MSubscribe.target == target_obj)
            )
            if target_count == 0:
                # delete empty target
                await session.delete(target_obj)
            await session.commit()

    async def update_subscribe(
        self,
        user: int,
        user_type: str,
        target: str,
        target_name: str,
        platform_name: str,
        cats: list,
        tags: list,
    ):
        async with AsyncSession(get_engine()) as sess:
            subscribe_obj: MSubscribe = await sess.scalar(
                select(MSubscribe)
                .where(
                    User.uid == user,
                    User.type == user_type,
                    MTarget.target == target,
                    MTarget.platform_name == platform_name,
                )
                .join(User)
                .join(MTarget)
                .options(selectinload(MSubscribe.target))  # type:ignore
            )
            subscribe_obj.tags = tags  # type:ignore
            subscribe_obj.categories = cats  # type:ignore
            subscribe_obj.target.target_name = target_name
            await sess.commit()


config = DBConfig()
