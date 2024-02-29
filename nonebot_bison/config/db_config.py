import asyncio
from collections import defaultdict
from datetime import time, datetime
from collections.abc import Callable, Sequence, Awaitable

from nonebot.compat import model_dump
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, delete, select
from nonebot_plugin_saa import PlatformTarget
from nonebot_plugin_datastore import create_session

from ..types import Tag
from ..types import Target as T_Target
from .utils import NoSuchTargetException
from .db_model import User, Target, Subscribe, ScheduleTimeWeight
from ..types import Category, UserSubInfo, WeightConfig, TimeWeightConfig, PlatformWeightConfigResp


def _get_time():
    dt = datetime.now()
    cur_time = time(hour=dt.hour, minute=dt.minute, second=dt.second)
    return cur_time


class SubscribeDupException(Exception): ...


class DBConfig:
    def __init__(self):
        self.add_target_hook: list[Callable[[str, T_Target], Awaitable]] = []
        self.delete_target_hook: list[Callable[[str, T_Target], Awaitable]] = []

    def register_add_target_hook(self, fun: Callable[[str, T_Target], Awaitable]):
        self.add_target_hook.append(fun)

    def register_delete_target_hook(self, fun: Callable[[str, T_Target], Awaitable]):
        self.delete_target_hook.append(fun)

    async def add_subscribe(
        self,
        user: PlatformTarget,
        target: T_Target,
        target_name: str,
        platform_name: str,
        cats: list[Category],
        tags: list[Tag],
    ):
        async with create_session() as session:
            db_user_stmt = select(User).where(User.user_target == model_dump(user))
            db_user: User | None = await session.scalar(db_user_stmt)
            if not db_user:
                db_user = User(user_target=model_dump(user))
                session.add(db_user)
            db_target_stmt = select(Target).where(Target.platform_name == platform_name).where(Target.target == target)
            db_target: Target | None = await session.scalar(db_target_stmt)
            if not db_target:
                db_target = Target(target=target, platform_name=platform_name, target_name=target_name)
                await asyncio.gather(*[hook(platform_name, target) for hook in self.add_target_hook])
            else:
                db_target.target_name = target_name
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

    async def list_subscribe(self, user: PlatformTarget) -> Sequence[Subscribe]:
        async with create_session() as session:
            query_stmt = (
                select(Subscribe)
                .where(User.user_target == model_dump(user))
                .join(User)
                .options(selectinload(Subscribe.target))
            )
            subs = (await session.scalars(query_stmt)).all()
            return subs

    async def list_subs_with_all_info(self) -> Sequence[Subscribe]:
        """获取数据库中带有user、target信息的subscribe数据"""
        async with create_session() as session:
            query_stmt = (
                select(Subscribe).join(User).options(selectinload(Subscribe.target), selectinload(Subscribe.user))
            )
            subs = (await session.scalars(query_stmt)).all()

        return subs

    async def del_subscribe(self, user: PlatformTarget, target: str, platform_name: str):
        async with create_session() as session:
            user_obj = await session.scalar(select(User).where(User.user_target == model_dump(user)))
            target_obj = await session.scalar(
                select(Target).where(Target.platform_name == platform_name, Target.target == target)
            )
            await session.execute(delete(Subscribe).where(Subscribe.user == user_obj, Subscribe.target == target_obj))
            target_count = await session.scalar(
                select(func.count()).select_from(Subscribe).where(Subscribe.target == target_obj)
            )
            if target_count == 0:
                # delete empty target
                await asyncio.gather(*[hook(platform_name, T_Target(target)) for hook in self.delete_target_hook])
            await session.commit()

    async def update_subscribe(
        self,
        user: PlatformTarget,
        target: str,
        target_name: str,
        platform_name: str,
        cats: list,
        tags: list,
    ):
        async with create_session() as sess:
            subscribe_obj: Subscribe = await sess.scalar(
                select(Subscribe)
                .where(
                    User.user_target == model_dump(user),
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

    async def get_platform_target(self, platform_name: str) -> Sequence[Target]:
        async with create_session() as sess:
            subq = select(Subscribe.target_id).distinct().subquery()
            query = select(Target).join(subq).where(Target.platform_name == platform_name)
            return (await sess.scalars(query)).all()

    async def get_time_weight_config(self, target: T_Target, platform_name: str) -> WeightConfig:
        async with create_session() as sess:
            time_weight_conf = (
                await sess.scalars(
                    select(ScheduleTimeWeight)
                    .where(Target.platform_name == platform_name, Target.target == target)
                    .join(Target)
                )
            ).all()
            targetObj = await sess.scalar(
                select(Target).where(Target.platform_name == platform_name, Target.target == target)
            )
            assert targetObj
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

    async def update_time_weight_config(self, target: T_Target, platform_name: str, conf: WeightConfig):
        async with create_session() as sess:
            targetObj = await sess.scalar(
                select(Target).where(Target.platform_name == platform_name, Target.target == target)
            )
            if not targetObj:
                raise NoSuchTargetException()
            target_id = targetObj.id
            targetObj.default_schedule_weight = conf.default
            delete_statement = delete(ScheduleTimeWeight).where(ScheduleTimeWeight.target_id == target_id)
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
        async with create_session() as sess:
            targets = (
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
                    if time_conf.start_time <= cur_time and time_conf.end_time > cur_time:
                        weight = time_conf.weight
                        break
                res[key] = weight
        return res

    async def get_platform_target_subscribers(self, platform_name: str, target: T_Target) -> list[UserSubInfo]:
        async with create_session() as sess:
            query = (
                select(Subscribe)
                .join(Target)
                .where(Target.platform_name == platform_name, Target.target == target)
                .options(selectinload(Subscribe.user))
            )
            subsribes = (await sess.scalars(query)).all()
            return [
                UserSubInfo(
                    PlatformTarget.deserialize(subscribe.user.user_target),
                    subscribe.categories,
                    subscribe.tags,
                )
                for subscribe in subsribes
            ]

    async def get_all_weight_config(
        self,
    ) -> dict[str, dict[str, PlatformWeightConfigResp]]:
        res: dict[str, dict[str, PlatformWeightConfigResp]] = defaultdict(dict)
        async with create_session() as sess:
            query = select(Target)
            targets = (await sess.scalars(query)).all()
            query = select(ScheduleTimeWeight).options(selectinload(ScheduleTimeWeight.target))
            time_weights = (await sess.scalars(query)).all()

        for target in targets:
            platform_name = target.platform_name
            if platform_name not in res.keys():
                res[platform_name][target.target] = PlatformWeightConfigResp(
                    target=T_Target(target.target),
                    target_name=target.target_name,
                    platform_name=platform_name,
                    weight=WeightConfig(default=target.default_schedule_weight, time_config=[]),
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
