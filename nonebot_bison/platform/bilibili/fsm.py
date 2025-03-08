import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import inspect
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Generic,
    NamedTuple,
    ParamSpec,
    Protocol,
    TypeAlias,
    TypedDict,
    TypeVar,
    overload,
    runtime_checkable,
)

from nonebot import logger


class StrEnum(str, Enum): ...


TAddon = TypeVar("TAddon", contravariant=True)
TState = TypeVar("TState", contravariant=True)
TEvent = TypeVar("TEvent", contravariant=True)
TFSM = TypeVar("TFSM", bound="FSM", contravariant=True)
P = ParamSpec("P")


class StateError(Exception): ...


ActionReturn: TypeAlias = Any


@runtime_checkable
class SupportStateOnExit(Generic[TAddon], Protocol):
    async def on_exit(self, addon: TAddon) -> None: ...


@runtime_checkable
class SupportStateOnEnter(Generic[TAddon], Protocol):
    async def on_enter(self, addon: TAddon) -> None: ...


class Action(Generic[TState, TEvent, TAddon], Protocol):
    async def __call__(self, from_: TState, event: TEvent, to: TState, addon: TAddon) -> ActionReturn: ...


ConditionFunc = Callable[[TAddon], Awaitable[bool]]


@dataclass(frozen=True)
class Condition(Generic[TAddon]):
    call: ConditionFunc[TAddon]
    not_: bool = False

    def __repr__(self):
        if inspect.isfunction(self.call) or inspect.isclass(self.call):
            call_str = self.call.__name__
        else:
            call_str = repr(self.call)
        return f"Condition(call={call_str})"

    async def __call__(self, addon: TAddon) -> bool:
        return (await self.call(addon)) ^ self.not_


# FIXME: Python 3.11+ 才支持 NamedTuple和TypedDict使用多继承添加泛型
# 所以什么时候 drop 3.10(?
if sys.version_info >= (3, 11) or TYPE_CHECKING:

    class Transition(Generic[TState, TEvent, TAddon], NamedTuple):
        action: Action[TState, TEvent, TAddon]
        to: TState
        conditions: AbstractSet[Condition[TAddon]] | None = None

    class StateGraph(Generic[TState, TEvent, TAddon], TypedDict):
        transitions: dict[
            TState,
            dict[
                TEvent,
                Transition[TState, TEvent, TAddon] | Sequence[Transition[TState, TEvent, TAddon]],
            ],
        ]
        initial: TState

else:

    class Transition(NamedTuple):
        action: Action
        to: Any
        conditions: AbstractSet[Condition] | None = None

    class StateGraph(TypedDict):
        transitions: dict[Any, dict[Any, Transition]]
        initial: Any


class FSM(Generic[TState, TEvent, TAddon]):
    def __init__(self, graph: StateGraph[TState, TEvent, TAddon], addon: TAddon):
        self.started = False
        self.graph = graph
        self.current_state = graph["initial"]
        self.machine = self._core()
        self.addon = addon

    async def _core(self) -> AsyncGenerator[ActionReturn, TEvent]:
        self.current_state = self.graph["initial"]
        res = None
        while True:
            event = yield res

            if not self.started:
                raise StateError("FSM not started, please call start() first")

            selected_transition = await self.cherry_pick(event)

            logger.trace(f"exit state: {self.current_state}")
            if isinstance(self.current_state, SupportStateOnExit):
                logger.trace(f"do {self.current_state}.on_exit")
                await self.current_state.on_exit(self.addon)

            logger.trace(f"do action: {selected_transition.action}")
            res = await selected_transition.action(self.current_state, event, selected_transition.to, self.addon)

            logger.trace(f"enter state: {selected_transition.to}")
            self.current_state = selected_transition.to

            if isinstance(self.current_state, SupportStateOnEnter):
                logger.trace(f"do {self.current_state}.on_enter")
                await self.current_state.on_enter(self.addon)

    async def start(self):
        await anext(self.machine)
        self.started = True
        logger.trace(f"FSM started, initial state: {self.current_state}")

    async def cherry_pick(self, event: TEvent) -> Transition[TState, TEvent, TAddon]:
        transitions = self.graph["transitions"][self.current_state].get(event)
        if transitions is None:
            raise StateError(f"Invalid event {event} in state {self.current_state}")

        if isinstance(transitions, Transition):
            return transitions
        elif isinstance(transitions, Sequence):
            no_conds: list[Transition[TState, TEvent, TAddon]] = []
            for transition in transitions:
                if not transition.conditions:
                    no_conds.append(transition)
                    continue

                values = await asyncio.gather(*(condition(self.addon) for condition in transition.conditions))

                if all(values):
                    logger.trace(f"conditions {transition.conditions} passed")
                    return transition
            else:
                if no_conds:
                    return no_conds.pop()
                else:
                    raise StateError(f"Invalid event {event} in state {self.current_state}")
        else:
            raise TypeError("Invalid transition type: {transitions}, expected Transition or Sequence[Transition]")

    async def emit(self, event: TEvent):
        return await self.machine.asend(event)

    async def reset(self):
        await self.machine.aclose()
        self.started = False

        del self.machine
        self.current_state = self.graph["initial"]
        self.machine = self._core()

        logger.trace("FSM closed")


@overload
def reset_on_exception(
    func: Callable[Concatenate[TFSM, P], Awaitable[ActionReturn]],
) -> Callable[Concatenate[TFSM, P], Awaitable[ActionReturn]]:
    """自动在发生异常后重置 FSM"""


@overload
def reset_on_exception(
    auto_start: bool = False,
) -> Callable[
    [Callable[Concatenate[TFSM, P], Awaitable[ActionReturn]]], Callable[Concatenate[TFSM, P], Awaitable[ActionReturn]]
]:
    """自动在异常后重置 FSM，当 auto_start 为 True 时，自动启动 FSM"""


# 参考自 dataclasses.dataclass 的实现
def reset_on_exception(func=None, /, *, auto_start=False):  # pyright: ignore[reportInconsistentOverload]
    def warp(func: Callable[Concatenate[TFSM, P], Awaitable[ActionReturn]]):
        return __reset_clear_up(func, auto_start)

    # 判断调用的是 @reset_on_exception 还是 @reset_on_exception(...)
    if func is None:
        # 调用的是带括号的
        return warp

    # 调用的是不带括号的
    return warp(func)


def __reset_clear_up(func: Callable[Concatenate[TFSM, P], Awaitable[ActionReturn]], auto_start: bool):
    @wraps(func)
    async def wrapper(fsm_self: TFSM, *args: P.args, **kwargs: P.kwargs) -> ActionReturn:
        try:
            return await func(fsm_self, *args, **kwargs)
        except Exception as e:
            logger.error(f"Exception in {func.__name__}: {e}")
            await fsm_self.reset()
            if auto_start and not fsm_self.started:
                await fsm_self.start()
            raise e

    return wrapper
