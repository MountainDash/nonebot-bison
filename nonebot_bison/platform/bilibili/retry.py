import sys
import random
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections.abc import Callable, Awaitable, Coroutine, AsyncGenerator
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, Protocol, TypeAlias, TypedDict, NamedTuple

from strenum import StrEnum
from nonebot.log import logger
from httpx import URL as HttpxURL

from nonebot_bison.types import Target

from .models import DynRawPost

if TYPE_CHECKING:
    from .platforms import Bilibili

TContext = TypeVar("TContext", contravariant=True)
TState = TypeVar("TState", bound=StrEnum, contravariant=True)
TEvent = TypeVar("TEvent", bound=StrEnum, contravariant=True)


class StateError(Exception): ...


class ApiCode352Error(Exception):
    def __init__(self, url: HttpxURL) -> None:
        msg = f"api {url} error"
        super().__init__(msg)


ActionReturn: TypeAlias = Any


class Action(Generic[TState, TEvent, TContext], Protocol):
    def __call__(
        self, from_: TState, event: TEvent, to: TState, ctx: TContext
    ) -> Coroutine[Any, Any, ActionReturn]: ...


# FIXME: Python 3.11+ 才支持 NamedTuple和TypedDict使用多继承添加泛型
# 所以什么时候 drop 3.10(?
if sys.version_info >= (3, 11) or TYPE_CHECKING:

    class Transition(Generic[TState, TEvent, TContext], NamedTuple):
        action: Action[TState, TEvent, TContext]
        to: TState

    class StateGraph(Generic[TState, TEvent, TContext], TypedDict):
        transitions: dict[TState, dict[TEvent, Transition[TState, TEvent, TContext]]]
        initial: TState

else:

    class Transition(NamedTuple):
        action: Action
        to: StrEnum

    class StateGraph(TypedDict):
        transitions: dict[StrEnum, dict[StrEnum, Transition]]
        initial: StrEnum


class FSM(Generic[TState, TEvent, TContext]):
    def __init__(self, graph: StateGraph[TState, TEvent, TContext], ctx: TContext):
        self.graph = graph
        self.current_state = graph["initial"]
        self.machine = self.core()
        self.ctx = ctx

    async def core(self) -> AsyncGenerator[ActionReturn, TEvent]:
        self.current_state = self.graph["initial"]
        res = None
        while True:
            event = yield res

            logger.trace(f"now state: {self.current_state}, receive event: {event}")
            transition = self.graph["transitions"][self.current_state].get(event)
            if transition is None:
                raise StateError(f"Invalid event {event} in state {self.current_state}")

            res = await transition.action(self.current_state, event, transition.to, self.ctx)
            logger.trace(f"after action ctx: {self.ctx}")
            logger.trace(f"action return: {res}")
            self.current_state = transition.to

    async def start(self):
        await anext(self.machine)

    async def emit(self, event: TEvent):
        return await self.machine.asend(event)


class RetryState(StrEnum):
    NROMAL = "normal"
    REFRESH = "refresh"
    BACKOFF = "backoff"
    RAISE = "raise"

    def __str__(self):
        return f"<retry state {self.name}>"


class RetryEvent(StrEnum):
    REQUEST_AND_SUCCESS = "request_and_success"
    REQUEST_AND_RAISE = "request_and_raise"
    REACH_MAX_REFRESH = "reach_max_refresh"
    REACH_MAX_BACKOFF = "reach_max_backoff"
    IN_BACKOFF_TIME = "in_backoff_time"
    OUT_BACKOFF_TIME = "out_backoff_time"

    def __str__(self):
        return f"<retry event {self.name}>"


@dataclass
class RetryContext:
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

    def reset_all(self):
        self.refresh_count = 0
        self.backoff_count = 0
        self.backoff_finish_time = None

    def reach_max(self, key: Literal["refresh", "backoff"]) -> bool:
        attr_name = f"{key}_count"
        if hasattr(self, attr_name):
            logger.trace(f"reach_max current {attr_name}: {getattr(self, attr_name)}")
            return getattr(self, attr_name) > (getattr(self, f"max_{attr_name}") - 1)
        raise KeyError(f"key {key} not found")

    def record_backoff_finish_time(self):
        self.backoff_finish_time = (
            datetime.now()
            + self.backoff_timedelta * (self.backoff_count + 1) ** 2
            # + timedelta(seconds=random.randint(1, 60)) # jitter
        )
        logger.trace(f"set backoff finish time: {self.backoff_finish_time}")

    def is_in_backoff_time(self):
        """是否在指数回避时间内"""
        # 指数回避
        if not self.backoff_finish_time:
            logger.trace("not in backoff time")
            return False

        logger.trace(f"now: {datetime.now()}, backoff_finish_time: {self.backoff_finish_time}")
        return datetime.now() < self.backoff_finish_time


class RetryActionReturn(StrEnum):
    REFRESH_MAX = "refresh_max"
    BACKOFF_MAX = "backoff_max"
    IN_BACKOFF = "in_backoff"
    OUT_BACKOFF = "out_backoff"

    def __str__(self):
        return f"<retry action return {self.name}>"


async def log_action(from_: RetryState, event: RetryEvent, to: RetryState, ctx: RetryContext) -> ActionReturn:
    logger.debug(f"log_action from {from_} to {to} by {event}")
    logger.trace(f"current context: {ctx}")
    return None


async def refresh_action(from_: RetryState, event: RetryEvent, to: RetryState, ctx: RetryContext) -> ActionReturn:
    logger.debug(f"refresh_action from {from_} to {to} by {event}")
    logger.trace(f"current context: {ctx}")
    assert from_ is RetryState.REFRESH

    if to is RetryState.NROMAL:
        ctx.reset_all()
        return

    if event is RetryEvent.REQUEST_AND_RAISE:
        ctx.refresh_count += 1
        logger.warning(f"刷新失败({ctx.refresh_count}/{ctx.max_refresh_count})，继续重试")

    if not ctx.reach_max("refresh"):
        return
    elif not ctx.reach_max("backoff"):
        # 刷新次数达到上限，但未达到指数回避次数上限，进入指数回避状态
        ctx.record_backoff_finish_time()
        ctx.refresh_count = 0
        return RetryActionReturn.REFRESH_MAX
    else:
        return RetryActionReturn.BACKOFF_MAX


async def backoff_action(from_: RetryState, event: RetryEvent, to: RetryState, ctx: RetryContext) -> ActionReturn:
    logger.debug(f"backoff_action from {from_} to {to} by {event}")
    logger.trace(f"current context: {ctx}")
    assert from_ is RetryState.BACKOFF

    if ctx.is_in_backoff_time():
        logger.warning("当前在指数回避时间内，继续等待")
        return RetryActionReturn.IN_BACKOFF

    if to is not RetryState.BACKOFF:
        logger.warning(f"本次指数回避时间结束({ctx.backoff_count + 1}/{ctx.max_backoff_count})")
        ctx.backoff_finish_time = None
        ctx.backoff_count += 1

    return RetryActionReturn.OUT_BACKOFF


async def raise_action(from_: RetryState, event: RetryEvent, to: RetryState, ctx: RetryContext) -> ActionReturn:
    logger.debug(f"raise_action from {from_} to {to} by {event}")
    logger.trace(f"current context: {ctx}")
    if to is RetryState.NROMAL:
        ctx.reset_all()
        return


RETRY_GRAPH: StateGraph[RetryState, RetryEvent, RetryContext] = {
    "transitions": {
        RetryState.NROMAL: {
            RetryEvent.REQUEST_AND_SUCCESS: Transition(log_action, RetryState.NROMAL),
            RetryEvent.REQUEST_AND_RAISE: Transition(log_action, RetryState.REFRESH),
        },
        RetryState.REFRESH: {
            RetryEvent.REACH_MAX_BACKOFF: Transition(refresh_action, RetryState.RAISE),
            RetryEvent.REACH_MAX_REFRESH: Transition(refresh_action, RetryState.BACKOFF),
            RetryEvent.REQUEST_AND_SUCCESS: Transition(refresh_action, RetryState.NROMAL),
            RetryEvent.REQUEST_AND_RAISE: Transition(refresh_action, RetryState.REFRESH),
        },
        RetryState.BACKOFF: {
            RetryEvent.IN_BACKOFF_TIME: Transition(backoff_action, RetryState.BACKOFF),
            RetryEvent.OUT_BACKOFF_TIME: Transition(backoff_action, RetryState.REFRESH),
        },
        RetryState.RAISE: {
            RetryEvent.REQUEST_AND_SUCCESS: Transition(raise_action, RetryState.NROMAL),
            RetryEvent.REQUEST_AND_RAISE: Transition(raise_action, RetryState.RAISE),
        },
    },
    "initial": RetryState.NROMAL,
}


B = TypeVar("B", bound="Bilibili")


def retry_for_352(api_func: Callable[[B, Target], Awaitable[list[DynRawPost]]]):
    fsm = FSM(RETRY_GRAPH, RetryContext())
    started = False

    @wraps(api_func)
    async def wrapper(bls: B, *args, **kwargs) -> list[DynRawPost]:
        nonlocal started, fsm
        if not started:
            await fsm.start()
            started = True
        match fsm.current_state:
            case RetryState.NROMAL:
                try:
                    res = await api_func(bls, *args, **kwargs)
                except ApiCode352Error:
                    logger.error("API 352 错误，进入重试状态")
                    await fsm.emit(RetryEvent.REQUEST_AND_RAISE)
                    return []
                else:
                    await fsm.emit(RetryEvent.REQUEST_AND_SUCCESS)
                    return res

            case RetryState.REFRESH:
                try:
                    await bls.ctx.refresh_client()
                    res = await api_func(bls, *args, **kwargs)
                except ApiCode352Error:
                    match await fsm.emit(RetryEvent.REQUEST_AND_RAISE):
                        case RetryActionReturn.REFRESH_MAX:
                            logger.error("刷新次数达到上限，进入指数回避状态")
                            await fsm.emit(RetryEvent.REACH_MAX_REFRESH)
                        case RetryActionReturn.BACKOFF_MAX:
                            logger.error("指数回避次数达到上限，放弃回避")
                            await fsm.emit(RetryEvent.REACH_MAX_BACKOFF)

                    return []
                else:
                    logger.success("刷新成功，返回正常状态")
                    await fsm.emit(RetryEvent.REQUEST_AND_SUCCESS)
                    return res

            case RetryState.BACKOFF:
                action_res = await fsm.emit(RetryEvent.IN_BACKOFF_TIME)

                if action_res is RetryActionReturn.OUT_BACKOFF:
                    logger.warning("离开指数回避状态")
                    action_res = await fsm.emit(RetryEvent.OUT_BACKOFF_TIME)

                return []

            case RetryState.RAISE:
                try:
                    if random.random() < 0.1236:  # magic number! 其实是随便写的0.618的两倍(
                        logger.trace("随机刷新Client")
                        await bls.ctx.refresh_client()
                    res = await api_func(bls, *args, **kwargs)
                except ApiCode352Error:
                    logger.error("请求失败，继续重试")
                    await fsm.emit(RetryEvent.REQUEST_AND_RAISE)
                    return []
                else:
                    logger.success("成功重试，返回正常状态")
                    await fsm.emit(RetryEvent.REQUEST_AND_SUCCESS)
                    return res

            case _:
                raise StateError(f"Invalid state {fsm.current_state}")

    return wrapper
