from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Awaitable, Callable, Optional

from nonebot_plugin_datastore.db import get_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.expression import delete, select
from sqlalchemy.sql.functions import func

from ..types import Category, Tag
from ..types import Target as T_Target
from .db_model import ScheduleTimeWeight, Subscribe, Target, User


def _get_time():
    dt = datetime.now()
    cur_time = time(hour=dt.hour, minute=dt.minute, second=dt.second)
    return cur_time


@dataclass
class TimeWeightConfig:
    start_time: time
    end_time: time
    weight: int


@dataclass
class WeightConfig:

    default: int
    time_config: list[TimeWeightConfig]


class DBConfig:
    def __init__(self):
        self.add_target_hook: Optional[Callable[[str, T_Target], Awaitable]] = None
        self.delete_target_hook: Optional[Callable[[str, T_Target], Awaitable]] = None

    def register_add_target_hook(self, fun: Callable[[str, T_Target], Awaitable]):
        self.add_target_hook = fun

    def register_delete_target_hook(self, fun: Callable[[str, T_Target], Awaitable]):
        self.delete_target_hook = fun

    async def add_subscribe(
        self,
        user: int,
        user_type: str,
        target: T_Target,
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
                select(Target)
                .where(Target.platform_name == platform_name)
                .where(Target.target == target)
            )
            db_target: Optional[Target] = await session.scalar(db_target_stmt)
            if not db_target:
                db_target = Target(
                    target=target, platform_name=platform_name, target_name=target_name
                )
                if self.add_target_hook:
                    await self.add_target_hook(platform_name, target)
            else:
                db_target.target_name = target_name  # type: ignore
            subscribe = Subscribe(
                categories=cats,
                tags=tags,
                user=db_user,
                target=db_target,
            )
            session.add(subscribe)
            await session.commit()

    async def list_subscribe(self, user: int, user_type: str) -> list[Subscribe]:
        async with AsyncSession(get_engine()) as session:
            query_stmt = (
                select(Subscribe)
                .where(User.type == user_type, User.uid == user)
                .join(User)
                .options(selectinload(Subscribe.target))  # type:ignore
            )
            subs: list[Subscribe] = (await session.scalars(query_stmt)).all()
            return subs

    async def del_subscribe(
        self, user: int, user_type: str, target: str, platform_name: str
    ):
        async with AsyncSession(get_engine()) as session:
            user_obj = await session.scalar(
                select(User).where(User.uid == user, User.type == user_type)
            )
            target_obj = await session.scalar(
                select(Target).where(
                    Target.platform_name == platform_name, Target.target == target
                )
            )
            await session.execute(
                delete(Subscribe).where(
                    Subscribe.user == user_obj, Subscribe.target == target_obj
                )
            )
            target_count = await session.scalar(
                select(func.count())
                .select_from(Subscribe)
                .where(Subscribe.target == target_obj)
            )
            if target_count == 0:
                # delete empty target
                # await session.delete(target_obj)
                if self.delete_target_hook:
                    await self.delete_target_hook(platform_name, T_Target(target))
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
            subscribe_obj: Subscribe = await sess.scalar(
                select(Subscribe)
                .where(
                    User.uid == user,
                    User.type == user_type,
                    Target.target == target,
                    Target.platform_name == platform_name,
                )
                .join(User)
                .join(Target)
                .options(selectinload(Subscribe.target))  # type:ignore
            )
            subscribe_obj.tags = tags  # type:ignore
            subscribe_obj.categories = cats  # type:ignore
            subscribe_obj.target.target_name = target_name
            await sess.commit()

    async def get_platform_target(self, platform_name: str) -> list[Target]:
        async with AsyncSession(get_engine()) as sess:
            subq = select(Subscribe.target_id).distinct().subquery()
            query = (
                select(Target).join(subq).where(Target.platform_name == platform_name)
            )
            return (await sess.scalars(query)).all()

    async def get_time_weight_config(
        self, target: T_Target, platform_name: str
    ) -> WeightConfig:
        async with AsyncSession(get_engine()) as sess:
            time_weight_conf: list[ScheduleTimeWeight] = (
                await sess.scalars(
                    select(ScheduleTimeWeight)
                    .where(
                        Target.platform_name == platform_name, Target.target == target
                    )
                    .join(Target)
                )
            ).all()
            targetObj: Target = await sess.scalar(
                select(Target).where(
                    Target.platform_name == platform_name, Target.target == target
                )
            )
            return WeightConfig(
                default=targetObj.default_schedule_weight,
                time_config=[
                    TimeWeightConfig(
                        start_time=time_conf.start_time,
                        end_time=time_conf.end_time,
                        weight=time_conf.weight,
                    )
                    for time_conf in time_weight_conf
                ],
            )

    async def update_time_weight_config(
        self, target: T_Target, platform_name: str, conf: WeightConfig
    ):
        async with AsyncSession(get_engine()) as sess:
            targetObj: Target = await sess.scalar(
                select(Target).where(
                    Target.platform_name == platform_name, Target.target == target
                )
            )
            target_id = targetObj.id
            targetObj.default_schedule_weight = conf.default
            delete(ScheduleTimeWeight).where(ScheduleTimeWeight.target_id == target_id)
            for time_conf in conf.time_config:
                new_conf = ScheduleTimeWeight(
                    start_time=time_conf.start_time,
                    end_time=time_conf.end_time,
                    weight=time_conf.weight,
                    target=targetObj,
                )
                sess.add(new_conf)

            await sess.commit()

    async def get_current_weight_val(self, platform_list: list[str]) -> dict[str, int]:
        res = {}
        cur_time = _get_time()
        async with AsyncSession(get_engine()) as sess:
            targets: list[Target] = (
                await sess.scalars(
                    select(Target)
                    .where(Target.platform_name.in_(platform_list))
                    .options(selectinload(Target.time_weight))
                )
            ).all()
            for target in targets:
                key = f"{target.platform_name}-{target.target}"
                weight = target.default_schedule_weight
                for time_conf in target.time_weight:
                    if (
                        time_conf.start_time <= cur_time
                        and time_conf.end_time > cur_time
                    ):
                        weight = time_conf.weight
                        break
                res[key] = weight
        return res


config = DBConfig()
