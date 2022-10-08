from collections import defaultdict
from datetime import datetime, time
from typing import Awaitable, Callable, Optional

from nonebot_plugin_datastore.db import get_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.expression import delete, select
from sqlalchemy.sql.functions import func

from ..types import Category, PlatformWeightConfigResp, Tag
from ..types import Target as T_Target
from ..types import TimeWeightConfig
from ..types import User as T_User
from ..types import UserSubInfo, WeightConfig
from .db_model import ScheduleTimeWeight, Subscribe, Target, User
from .utils import NoSuchTargetException


def _get_time():
    dt = datetime.now()
    cur_time = time(hour=dt.hour, minute=dt.minute, second=dt.second)
    return cur_time


class SubscribeDupException(Exception):
    ...


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
            try:
                await session.commit()
            except IntegrityError as e:
                if len(e.args) > 0 and "UNIQUE constraint failed" in e.args[0]:
                    raise SubscribeDupException()
                raise e

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
            if not targetObj:
                raise NoSuchTargetException()
            target_id = targetObj.id
            targetObj.default_schedule_weight = conf.default
            delete_statement = delete(ScheduleTimeWeight).where(
                ScheduleTimeWeight.target_id == target_id
            )
            await sess.execute(delete_statement)
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

    async def get_platform_target_subscribers(
        self, platform_name: str, target: T_Target
    ) -> list[UserSubInfo]:
        async with AsyncSession(get_engine()) as sess:
            query = (
                select(Subscribe)
                .join(Target)
                .where(Target.platform_name == platform_name, Target.target == target)
                .options(selectinload(Subscribe.user))
            )
            subsribes: list[Subscribe] = (await sess.scalars(query)).all()
            return list(
                map(
                    lambda subscribe: UserSubInfo(
                        T_User(subscribe.user.uid, subscribe.user.type),
                        subscribe.categories,
                        subscribe.tags,
                    ),
                    subsribes,
                )
            )

    async def get_all_weight_config(
        self,
    ) -> dict[str, dict[str, PlatformWeightConfigResp]]:
        res: dict[str, dict[str, PlatformWeightConfigResp]] = defaultdict(dict)
        async with AsyncSession(get_engine()) as sess:
            query = select(Target)
            targets: list[Target] = (await sess.scalars(query)).all()
            query = select(ScheduleTimeWeight).options(
                selectinload(ScheduleTimeWeight.target)
            )
            time_weights: list[ScheduleTimeWeight] = (await sess.scalars(query)).all()

        for target in targets:
            platform_name = target.platform_name
            if platform_name not in res.keys():
                res[platform_name][target.target] = PlatformWeightConfigResp(
                    target=T_Target(target.target),
                    target_name=target.target_name,
                    platform_name=platform_name,
                    weight=WeightConfig(
                        default=target.default_schedule_weight, time_config=[]
                    ),
                )

        for time_weight_config in time_weights:
            platform_name = time_weight_config.target.platform_name
            target = time_weight_config.target.target
            res[platform_name][target].weight.time_config.append(
                TimeWeightConfig(
                    start_time=time_weight_config.start_time,
                    end_time=time_weight_config.end_time,
                    weight=time_weight_config.weight,
                )
            )
        return res


config = DBConfig()
