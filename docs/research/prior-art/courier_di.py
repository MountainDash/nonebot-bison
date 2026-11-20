"""courier_di.py — an 80-line DI kernel distilled from Entari/letoderea.

  * one mutable registry: dict[key -> _Spec]; key = a type, or (type, *markers)
    for Annotated[T, marker], so two providers of one type can coexist
  * signatures are read once with typing.get_type_hints(include_extras=True)
    at *declaration* time, so an unsatisfiable station raises there
  * a provider is any zero-arg callable; awaitables are awaited
  * singleton by default, per-call with singleton=False
  * a provider may itself declare needs (Entari's Depends); its signature is
    compiled by the same _plan(), and the resolve stack catches cycles
"""

from __future__ import annotations

import inspect
from typing import Annotated, Any, Callable, get_args, get_origin, get_type_hints


class DIError(Exception):
    """Base class for every resolution error."""


class MissingProviders(DIError):
    def __init__(self, owner: Any, missing: list[str]) -> None:
        self.owner, self.missing = owner, missing
        super().__init__(f"{owner!r} needs unregistered: {', '.join(missing)}")


class _Spec:
    __slots__ = ("factory", "singleton", "value", "resolved", "plan")

    def __init__(self, factory: Callable[..., Any], singleton: bool) -> None:
        self.factory, self.singleton, self.resolved, self.value = factory, singleton, False, None
        self.plan = _plan(factory)


_registry: dict[Any, _Spec] = {}


def _key(annotation: Any) -> Any:
    if get_origin(annotation) is Annotated:
        base, *markers = get_args(annotation)
        return (base, *markers) if markers else base
    return annotation


def register(key: Any, factory: Callable[..., Any], *, singleton: bool = True) -> None:
    k = _key(key)
    if k in _registry:
        raise DIError(f"{k!r} already has a provider")
    _registry[k] = _Spec(factory, singleton)


def provider(key: Any, *, singleton: bool = True) -> Callable[..., Any]:
    def deco(factory: Callable[..., Any]) -> Callable[..., Any]:
        register(key, factory, singleton=singleton)
        return factory

    return deco


async def resolve(key: Any, _stack: tuple[Any, ...] = ()) -> Any:
    k = _key(key)
    if k in _stack:
        raise DIError("circular dependency: " + " -> ".join(map(repr, (*_stack, k))))
    spec = _registry.get(k)
    if spec is None:
        raise MissingProviders(resolve, [repr(k)])
    if spec.singleton and spec.resolved:
        return spec.value
    value = spec.factory(**{n: await resolve(dep, (*_stack, k)) for n, dep in spec.plan})
    if inspect.isawaitable(value):
        value = await value
    if spec.singleton:
        spec.value, spec.resolved = value, True
    return value


def _plan(fn: Callable[..., Any]) -> list[tuple[str, Any]]:
    hints = get_type_hints(fn, include_extras=True)
    plan = []
    for name, param in inspect.signature(fn).parameters.items():
        if name not in hints:
            if param.default is inspect.Parameter.empty:
                raise DIError(f"{fn.__qualname__}: parameter {name!r} needs a type hint")
            continue
        plan.append((name, _key(hints[name])))
    return plan


def inject(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a station as injectable; every need is validated here, once."""
    plan = _plan(fn)
    missing = [f"{n}: {k!r}" for n, k in plan if k not in _registry]
    if missing:
        raise MissingProviders(fn, missing)
    fn.__di_plan__ = plan  # type: ignore[attr-defined]
    return fn


async def call(fn: Callable[..., Any], /, **provided: Any) -> Any:
    """Invoke `fn`, resolving only the parameters not passed explicitly."""
    plan = getattr(fn, "__di_plan__", None) or _plan(fn)
    kwargs = {**provided}
    for name, key in plan:
        if name not in provided:
            kwargs[name] = await resolve(key)
    result = fn(**kwargs)
    return await result if inspect.isawaitable(result) else result
