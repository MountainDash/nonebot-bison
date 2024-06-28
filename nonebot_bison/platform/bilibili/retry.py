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

TState = TypeVar("TState", bound=StrEnum, contravariant=True)
TEvent = TypeVar("TEvent", bound=StrEnum, contravariant=True)


class StateError(Exception): ...


class ApiCode352Error(Exception):
    def __init__(self, url: HttpxURL) -> None:
        msg = f"api {url} error"
        super().__init__(msg)


ActionReturn: TypeAlias = Any


class Action(Generic[TState, TEvent], Protocol):
    def __call__(self, from_: TState, event: TEvent, to: TState) -> Coroutine[Any, Any, ActionReturn]: ...


class Transition(Generic[TState, TEvent], NamedTuple):
    action: Action[TState, TEvent]
    to: TState


class StateGraph(Generic[TState, TEvent], TypedDict):
    transitions: dict[TState, dict[TEvent, Transition[TState, TEvent]]]
    initial: TState


class FSM(Generic[TState, TEvent]):
    def __init__(self, graph: StateGraph[TState, TEvent]):
        self.graph = graph
        self.current_state = graph["initial"]
        self.machine = self.core()

    async def core(self) -> AsyncGenerator[ActionReturn, TEvent]:
        self.current_state = self.graph["initial"]
        res = None
        while True:
            event = yield res

            logger.trace(f"now state: {self.current_state}, receive event: {event}")
            transition = self.graph["transitions"][self.current_state].get(event)
            if transition is None:
                # logger.error(f"Invalid event {event} in state {state}")
                raise StateError(f"Invalid event {event} in state {self.current_state}")

            res = await transition.action(self.current_state, event, transition.to)
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


async def log_action(from_: RetryState, event: RetryEvent, to: RetryState) -> ActionReturn:
    logger.debug(f"log_action from {from_} to {to} by {event}")
    return None


RETRY_GRAPH: StateGraph[RetryState, RetryEvent] = {
    "transitions": {
        RetryState.NROMAL: {
            RetryEvent.REQUEST_AND_SUCCESS: Transition(log_action, RetryState.NROMAL),
            RetryEvent.REQUEST_AND_RAISE: Transition(log_action, RetryState.REFRESH),
        },
        RetryState.REFRESH: {
            RetryEvent.REACH_MAX_REFRESH: Transition(log_action, RetryState.BACKOFF),
            RetryEvent.REQUEST_AND_SUCCESS: Transition(log_action, RetryState.NROMAL),
            RetryEvent.REQUEST_AND_RAISE: Transition(log_action, RetryState.REFRESH),
        },
        RetryState.BACKOFF: {
            RetryEvent.IN_BACKOFF_TIME: Transition(log_action, RetryState.BACKOFF),
            RetryEvent.OUT_BACKOFF_TIME: Transition(log_action, RetryState.REFRESH),
            RetryEvent.REACH_MAX_BACKOFF: Transition(log_action, RetryState.RAISE),
        },
        RetryState.RAISE: {
            RetryEvent.REQUEST_AND_SUCCESS: Transition(log_action, RetryState.NROMAL),
            RetryEvent.REQUEST_AND_RAISE: Transition(log_action, RetryState.RAISE),
        },
    },
    "initial": RetryState.NROMAL,
}


@dataclass
class Context:
    refresh_count = 0
    backoff_count = 0
    backoff_start_time: datetime | None = None

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
        self.backoff_start_time = None

    def reach_max(self, key: Literal["refresh", "backoff"]):
        attr_name = f"{key}_count"
        if hasattr(self, attr_name):
            logger.trace(f"reach max current {attr_name}: {getattr(self, attr_name)}")
            return getattr(self, attr_name) > (getattr(self, f"max_{attr_name}") - 1)
        raise KeyError(f"key {key} not found")

    def is_in_backoff_time(self):
        """是否在指数回避时间内"""
        # 指数回避
        if not self.backoff_start_time:
            raise ValueError("backoff_start_time is None")

        now = datetime.now()
        logger.trace(f"current backoff count: {self.backoff_count}")
        logger.trace(f"backoff start time: {self.backoff_start_time}")
        logger.trace(f"now: {now}")

        should_wait = self.backoff_timedelta * (self.backoff_count + 1) ** 2
        logger.trace(f"should wait: {should_wait}")

        waited = now - self.backoff_start_time
        logger.trace(f"waited: {waited}")

        return waited < should_wait


B = TypeVar("B", bound="Bilibili")


def retry_for_352(api_func: Callable[[B, Target], Awaitable[list[DynRawPost]]]):
    fsm = FSM(RETRY_GRAPH)
    ctx = Context()
    started = False

    @wraps(api_func)
    async def wrapper(bls: B, *args, **kwargs) -> list[DynRawPost]:
        nonlocal started, fsm, ctx
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
                    logger.warning(f"刷新失败({ctx.refresh_count + 1}/{ctx.max_refresh_count})，继续重试")
                    ctx.refresh_count += 1

                    if ctx.reach_max("refresh"):
                        logger.error("刷新次数达到上限，进入指数回避状态")
                        ctx.backoff_start_time = datetime.now()
                        logger.trace(f"记录指数回避时间：{ctx.backoff_start_time}")
                        ctx.refresh_count = 0
                        await fsm.emit(RetryEvent.REACH_MAX_REFRESH)
                        return []

                    await fsm.emit(RetryEvent.REQUEST_AND_RAISE)
                    return []
                else:
                    logger.success("刷新成功，返回正常状态")
                    ctx.reset_all()
                    await fsm.emit(RetryEvent.REQUEST_AND_SUCCESS)
                    return res

            case RetryState.BACKOFF:
                if not ctx.is_in_backoff_time():
                    logger.warning(
                        f"本次指数回避时间结束({ctx.backoff_count + 1}/{ctx.max_backoff_count})，返回刷新状态"
                    )
                    ctx.backoff_start_time = None
                    ctx.backoff_count += 1

                    if ctx.reach_max("backoff"):
                        logger.error("指数回避次数达到上限，抛出异常")
                        await fsm.emit(RetryEvent.REACH_MAX_BACKOFF)
                        return []

                    await fsm.emit(RetryEvent.OUT_BACKOFF_TIME)
                    return []

                logger.warning("当前在指数回避时间内，继续等待")
                await fsm.emit(RetryEvent.IN_BACKOFF_TIME)
                return []

            case RetryState.RAISE:
                try:
                    if random.random() < 0.1236:
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
