from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
import random
from typing import TYPE_CHECKING, Generic, Literal, TypeVar
from typing_extensions import assert_never, override

from httpx import URL as HttpxURL
from nonebot.log import logger
from strenum import StrEnum

from nonebot_bison.types import Target

from .fsm import FSM, ActionReturn, Condition, StateGraph, Transition, reset_on_exception
from .models import DynRawPost

if TYPE_CHECKING:
    from .platforms import Bilibili

# 不用 TypeVar 的话，使用装饰器 Pyright 会报错
TBilibili = TypeVar("TBilibili", bound="Bilibili")


class ApiCode352Error(Exception):
    def __init__(self, url: HttpxURL) -> None:
        msg = f"api {url} error"
        super().__init__(msg)


# see https://docs.python.org/zh-cn/3/howto/enum.html#dataclass-support
@dataclass(frozen=True)
class StateMixin:
    state: Literal["NORMAL", "REFRESH", "BACKOFF", "RAISE"]
    enter_func: Callable[["RetryAddon"], Awaitable[None]] | None = None
    exit_func: Callable[["RetryAddon"], Awaitable[None]] | None = None

    async def on_enter(self, addon: "RetryAddon"):
        if self.enter_func:
            await self.enter_func(addon)

    async def on_exit(self, addon: "RetryAddon"):
        if self.exit_func:
            await self.exit_func(addon)

    def __str__(self):
        return f"<retry state {self.state}>"


async def on_normal_enter(addon: "RetryAddon"):
    addon.reset_all()


async def on_refresh_enter(addon: "RetryAddon"):
    addon.refresh_count += 1
    await addon.refresh_client()
    logger.warning(f"当前刷新次数: {addon.refresh_count}/{addon.max_refresh_count}")


async def on_raise_enter(addon: "RetryAddon"):
    if random.random() < 0.1236:
        await addon.refresh_client()
        logger.warning("触发随机刷新")


class RetryState(StateMixin, Enum):
    NROMAL = "NORMAL", on_normal_enter
    REFRESH = "REFRESH", on_refresh_enter
    BACKOFF = "BACKOFF"
    RAISE = "RAISE", on_raise_enter

    def __str__(self):
        return f"<retry state {self.name}>"


class RetryEvent(StrEnum):
    REQUEST_AND_SUCCESS = "request_and_success"
    REQUEST_AND_RAISE = "request_and_raise"
    IN_BACKOFF_TIME = "in_backoff_time"

    def __str__(self):
        return f"<retry event {self.name}>"


@dataclass
class RetryAddon(Generic[TBilibili]):
    bilibili_platform: TBilibili | None = None
    refresh_count: int = 0
    backoff_count: int = 0
    backoff_finish_time: datetime | None = None

    @property
    def max_refresh_count(cls):
        return 3

    @property
    def max_backoff_count(self):
        return 3

    @property
    def backoff_timedelta(self):
        return timedelta(minutes=5)

    async def refresh_client(self):
        if self.bilibili_platform:
            await self.bilibili_platform.ctx.refresh_client()
        else:
            raise RuntimeError("未设置 bilibili_platform")

    def reset_all(self):
        self.refresh_count = 0
        self.backoff_count = 0
        self.backoff_finish_time = None

    def record_backoff_finish_time(self):
        self.backoff_finish_time = (
            datetime.now() + self.backoff_timedelta * self.backoff_count**2
            # + timedelta(seconds=random.randint(1, 60)) # jitter
        )
        logger.trace(f"set backoff finish time: {self.backoff_finish_time}")

    def is_in_backoff_time(self):
        """是否在指数回避时间内"""
        # 指数回避
        if not self.backoff_finish_time:
            logger.trace("not have backoff_finish_time")
            return False

        logger.trace(f"now: {datetime.now()}, backoff_finish_time: {self.backoff_finish_time}")
        return datetime.now() < self.backoff_finish_time


async def action_log(from_: RetryState, event: RetryEvent, to: RetryState, addon: RetryAddon) -> ActionReturn:
    logger.debug(f"{from_} -> {to}, by {event}")


async def action_up_to_backoff(from_: RetryState, event: RetryEvent, to: RetryState, addon: RetryAddon) -> ActionReturn:
    addon.refresh_count = 0
    addon.backoff_count += 1
    addon.record_backoff_finish_time()
    logger.warning(
        f"当前已回避次数: {addon.backoff_count}/{addon.max_backoff_count}, 本次回避时间至 {addon.backoff_finish_time}"
    )


async def action_back_to_refresh(
    from_: RetryState, event: RetryEvent, to: RetryState, addon: RetryAddon
) -> ActionReturn:
    addon.backoff_finish_time = None
    logger.debug("back to refresh state")


async def is_reach_max_refresh(addon: RetryAddon) -> bool:
    return addon.refresh_count > addon.max_refresh_count - 1


async def is_reach_max_backoff(addon: RetryAddon) -> bool:
    return addon.backoff_count > addon.max_backoff_count - 1


async def is_out_backoff_time(addon: RetryAddon) -> bool:
    return not addon.is_in_backoff_time()


RETRY_GRAPH: StateGraph[RetryState, RetryEvent, RetryAddon] = {
    "transitions": {
        RetryState.NROMAL: {
            RetryEvent.REQUEST_AND_SUCCESS: Transition(action_log, RetryState.NROMAL),
            RetryEvent.REQUEST_AND_RAISE: Transition(action_log, RetryState.REFRESH),
        },
        RetryState.REFRESH: {
            RetryEvent.REQUEST_AND_SUCCESS: Transition(action_log, RetryState.NROMAL),
            RetryEvent.REQUEST_AND_RAISE: [
                Transition(action_log, RetryState.REFRESH),
                Transition(
                    action_up_to_backoff,
                    RetryState.BACKOFF,
                    {
                        Condition(is_reach_max_refresh),
                        Condition(is_reach_max_backoff, not_=True),
                    },
                ),
                Transition(
                    action_log,
                    RetryState.RAISE,
                    {
                        Condition(is_reach_max_refresh),
                        Condition(is_reach_max_backoff),
                    },
                ),
            ],
        },
        RetryState.BACKOFF: {
            RetryEvent.IN_BACKOFF_TIME: [
                Transition(action_log, RetryState.BACKOFF),
                Transition(action_back_to_refresh, RetryState.REFRESH, {Condition(is_out_backoff_time)}),
            ],
        },
        RetryState.RAISE: {
            RetryEvent.REQUEST_AND_SUCCESS: Transition(action_log, RetryState.NROMAL),
            RetryEvent.REQUEST_AND_RAISE: Transition(action_log, RetryState.RAISE),
        },
    },
    "initial": RetryState.NROMAL,
}


class RetryFSM(FSM[RetryState, RetryEvent, RetryAddon[TBilibili]]):
    @override
    async def start(self, bls: TBilibili):
        self.addon.bilibili_platform = bls
        await super().start()

    @override
    async def reset(self):
        self.addon.reset_all()
        await super().reset()

    @override
    @reset_on_exception
    async def emit(self, event: RetryEvent):
        await super().emit(event)


# FIXME: 拿出来是方便测试了，但全局单例会导致所有被装饰的函数共享状态，有待改进
_retry_fsm = RetryFSM(RETRY_GRAPH, RetryAddon["Bilibili"]())


def retry_for_352(api_func: Callable[[TBilibili, Target], Awaitable[list[DynRawPost]]]):
    # _retry_fsm = RetryFSM(RETRY_GRAPH, RetryAddon[TBilibili]())

    @wraps(api_func)
    async def wrapper(bls: TBilibili, *args, **kwargs) -> list[DynRawPost]:
        # nonlocal _retry_fsm
        if not _retry_fsm.started:
            await _retry_fsm.start(bls)

        match _retry_fsm.current_state:
            case RetryState.NROMAL | RetryState.REFRESH | RetryState.RAISE:
                try:
                    res = await api_func(bls, *args, **kwargs)
                except ApiCode352Error as e:
                    logger.warning("本次 Bilibili API 请求返回 352 错误码")
                    await _retry_fsm.emit(RetryEvent.REQUEST_AND_RAISE)

                    if _retry_fsm.current_state == RetryState.RAISE:
                        raise e

                    return []
                else:
                    await _retry_fsm.emit(RetryEvent.REQUEST_AND_SUCCESS)
                    return res
            case RetryState.BACKOFF:
                logger.warning("本次 Bilibili 请求回避中，不请求")
                await _retry_fsm.emit(RetryEvent.IN_BACKOFF_TIME)
                return []
            case _:
                assert_never(_retry_fsm.current_state)

    return wrapper
