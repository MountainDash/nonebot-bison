from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol, cast, final

from arclet.letoderea import Param, Provider, ProviderFactory

from .model import Binding, BindingPlan, ParameterSpec, ProviderSpec, RegistrySnapshot, compile_plan


class BindingBackend(Protocol):
    def bind(self, parameter: ParameterSpec, snapshot: RegistrySnapshot) -> tuple[Binding, ...]: ...


class _TypedProviderFactory(Protocol):
    def validate(self, param: Param) -> Provider[object] | None: ...


@final
class ExactKeyBindingBackend:
    def bind(self, parameter: ParameterSpec, snapshot: RegistrySnapshot) -> tuple[Binding, ...]:
        return tuple(Binding(provider) for provider in snapshot.providers if provider.key == parameter.key)


@final
class LetodereaPredicateBindingBackend:
    """Adapt only explicitly registered arclet candidates; metadata never adds context providers."""

    def bind(self, parameter: ParameterSpec, snapshot: RegistrySnapshot) -> tuple[Binding, ...]:
        param = Param(parameter.name, parameter.key.base, parameter.default, parameter.key.markers, [])
        bindings: list[Binding] = []
        for spec in snapshot.providers:
            candidate = spec.native
            if candidate is None:
                continue
            if isinstance(candidate, ProviderFactory):
                # arclet 0.22 leaves the generated Provider generic parameter unknown.
                provider = cast("_TypedProviderFactory", candidate).validate(param)
                if provider is None:
                    continue
            elif candidate.validate(param):
                provider = candidate
            else:
                continue
            bindings.append(Binding(spec, provider, provider.priority))
        return tuple(bindings)


def _bind_one(plan: BindingPlan, snapshot: RegistrySnapshot, backends: Sequence[BindingBackend]) -> BindingPlan:
    bindings = tuple(
        tuple(candidate for backend in backends for candidate in backend.bind(parameter, snapshot))
        for parameter in plan.parameters
    )
    return replace(plan, bindings=bindings)


def bind_plan(
    plan: BindingPlan,
    snapshot: RegistrySnapshot,
    backends: Sequence[BindingBackend] | None = None,
) -> BindingPlan:
    """Bind a root and its local Depends graph; cycles remain as data for validation."""
    selected = (ExactKeyBindingBackend(),) if backends is None else backends
    plans: dict[int, BindingPlan] = {}

    def visit(current: BindingPlan) -> None:
        identity = id(current.target)
        if identity in plans:
            return
        bound = _bind_one(current, snapshot, selected)
        plans[identity] = bound
        for parameter in current.parameters:
            if parameter.depends is not None:
                visit(compile_plan(parameter.depends.target))

    visit(plan)
    root = plans[id(plan.target)]
    return replace(root, dependencies=tuple(item for identity, item in plans.items() if identity != id(plan.target)))


def bind_providers(
    snapshot: RegistrySnapshot,
    backends: Sequence[BindingBackend] | None = None,
) -> RegistrySnapshot:
    selected = (ExactKeyBindingBackend(),) if backends is None else backends
    providers: list[ProviderSpec] = []
    for provider in snapshot.providers:
        bound = None if provider.plan is None else bind_plan(provider.plan, snapshot, selected)
        providers.append(provider if bound is None else replace(provider, plan=bound))
    return RegistrySnapshot(tuple(providers))
