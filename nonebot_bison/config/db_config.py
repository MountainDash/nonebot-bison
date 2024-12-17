import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, time

from nonebot.compat import model_dump
from nonebot_plugin_datastore import create_session
from nonebot_plugin_saa import PlatformTarget
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from nonebot_bison.types import Category, PlatformWeightConfigResp, Tag, TimeWeightConfig, UserSubInfo, WeightConfig
from nonebot_bison.types import Target as T_Target

from .db_model import Cookie, CookieTarget, ScheduleTimeWeight, Subscribe, Target, User
from .utils import DuplicateCookieTargetException, NoSuchTargetException


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

    async def get_cookie(
        self,
        site_name: str | None = None,
        target: T_Target | None = None,
        is_universal: bool | None = None,
        is_anonymous: bool | None = None,
    ) -> Sequence[Cookie]:
        """获取满足传入条件的所有 cookie"""
        async with create_session() as sess:
            query = select(Cookie).distinct()
            if is_universal is not None:
                query = query.where(Cookie.is_universal == is_universal)
            if is_anonymous is not None:
                query = query.where(Cookie.is_anonymous == is_anonymous)
            if site_name:
                query = query.where(Cookie.site_name == site_name)
            query = query.outerjoin(CookieTarget).options(selectinload(Cookie.targets))
            res = (await sess.scalars(query)).all()
            if target:
                # 如果指定了 target，过滤掉不满足要求的cookie
                query = select(CookieTarget.cookie_id).join(Target).where(Target.target == target)
                ids = set((await sess.scalars(query)).all())
                # 如果指定了 target 且未指定 is_universal，则添加返回 universal cookie
                res = [cookie for cookie in res if cookie.id in ids or cookie.is_universal]
            return res

    async def get_cookie_by_id(self, cookie_id: int) -> Cookie:
        async with create_session() as sess:
            cookie = await sess.scalar(select(Cookie).where(Cookie.id == cookie_id))
            if not cookie:
                raise NoSuchTargetException(f"cookie {cookie_id} not found")
            return cookie

    async def add_cookie(self, cookie: Cookie) -> int:
        async with create_session() as sess:
            sess.add(cookie)
            await sess.commit()
            await sess.refresh(cookie)
            return cookie.id

    async def update_cookie(self, cookie: Cookie):
        async with create_session() as sess:
            cookie_in_db: Cookie | None = await sess.scalar(select(Cookie).where(Cookie.id == cookie.id))
            if not cookie_in_db:
                raise ValueError(f"cookie {cookie.id} not found")
            cookie_in_db.content = cookie.content
            cookie_in_db.cookie_name = cookie.cookie_name
            cookie_in_db.last_usage = cookie.last_usage
            cookie_in_db.status = cookie.status
            cookie_in_db.tags = cookie.tags
            await sess.commit()

    async def delete_cookie_by_id(self, cookie_id: int):
        async with create_session() as sess:
            cookie = await sess.scalar(
                select(Cookie)
                .where(Cookie.id == cookie_id)
                .outerjoin(CookieTarget)
                .options(selectinload(Cookie.targets))
            )
            if not cookie:
                raise NoSuchTargetException(f"cookie {cookie_id} not found")
            if len(cookie.targets) > 0:
                raise Exception(f"cookie {cookie.id} in use")
            await sess.execute(delete(Cookie).where(Cookie.id == cookie_id))
            await sess.commit()

    async def add_cookie_target(self, target: T_Target, platform_name: str, cookie_id: int):
        """通过 cookie_id 可以唯一确定一个 Cookie，通过 target 和 platform_name 可以唯一确定一个 Target"""
        async with create_session() as sess:
            target_obj = await sess.scalar(
                select(Target).where(Target.platform_name == platform_name, Target.target == target)
            )
            # check if relation exists
            cookie_target = await sess.scalar(
                select(CookieTarget).where(CookieTarget.target == target_obj, CookieTarget.cookie_id == cookie_id)
            )
            if cookie_target:
                raise DuplicateCookieTargetException()
            cookie_obj = await sess.scalar(select(Cookie).where(Cookie.id == cookie_id))
            cookie_target = CookieTarget(target=target_obj, cookie=cookie_obj)
            sess.add(cookie_target)
            await sess.commit()

    async def delete_cookie_target(self, target: T_Target, platform_name: str, cookie_id: int):
        async with create_session() as sess:
            target_obj = await sess.scalar(
                select(Target).where(Target.platform_name == platform_name, Target.target == target)
            )
            cookie_obj = await sess.scalar(select(Cookie).where(Cookie.id == cookie_id))
            await sess.execute(
                delete(CookieTarget).where(CookieTarget.target == target_obj, CookieTarget.cookie == cookie_obj)
            )
            await sess.commit()

    async def delete_cookie_target_by_id(self, cookie_target_id: int):
        async with create_session() as sess:
            await sess.execute(delete(CookieTarget).where(CookieTarget.id == cookie_target_id))
            await sess.commit()

    async def get_cookie_target(self) -> list[CookieTarget]:
        async with create_session() as sess:
            query = (
                select(CookieTarget)
                .outerjoin(Target)
                .options(selectinload(CookieTarget.target))
                .outerjoin(Cookie)
                .options(selectinload(CookieTarget.cookie))
            )
            res = list((await sess.scalars(query)).all())
            res.sort(key=lambda x: (x.target.platform_name, x.cookie_id, x.target_id))
            return res

    async def clear_db(self):
        """清空数据库，用于单元测试清理环境"""
        async with create_session() as sess:
            await sess.execute(delete(User))
            await sess.execute(delete(Target))
            await sess.execute(delete(ScheduleTimeWeight))
            await sess.execute(delete(Subscribe))
            await sess.execute(delete(Cookie))
            await sess.execute(delete(CookieTarget))
            await sess.commit()


config = DBConfig()
