import inspect
from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass
from functools import wraps
from typing import Annotated, Any, cast, final, get_args, get_type_hints, overload, override

from anyio import Lock
from arclet.letoderea import Contexts, Depend, Force, Param, Provider, ProviderFactory, Subscriber

from .binding import BindingBackend, ExactKeyBindingBackend, bind_plan, bind_providers
from .errors import (
    DependencyValidationError,
    DispatcherFrozenError,
    DispatcherNotFrozenError,
    DuplicateProviderError,
    ResolutionError,
    SignatureError,
)
from .model import (
    BindingPlan,
    DependencyKey,
    Factory,
    ProviderSpec,
    RegistrySnapshot,
    ValidationIssue,
    ValidationReport,
    compile_plan,
)
from .validation import StrictGraphValidationBackend, ValidationBackend


@dataclass(slots=True)
class _Compiled:
    snapshot: RegistrySnapshot
    plans: dict[int, BindingPlan]


@final
class _OverrideProvider(Provider[object]):
    def __init__(self, context_key: str | None, parameter: str) -> None:
        super().__init__()
        self.context_key = context_key
        self.parameter = parameter

    @override
    def validate(self, param: Param) -> bool:
        return any(marker is self for marker in param.meta)

    @override
    async def __call__(self, context: Contexts) -> Force | None:
        if self.context_key is None:
            return None
        overrides: Mapping[str, object] = context.get(self.context_key, {})
        return Force(overrides[self.parameter]) if self.parameter in overrides else None


@final
class _ExactProvider(Provider[object]):
    def __init__(
        self,
        dispatcher: DependencyDispatcher,
        spec: ProviderSpec,
        owner: str,
        parameter: str,
        overrides_key: str | None,
    ) -> None:
        super().__init__()
        self.dispatcher = dispatcher
        self.spec = spec
        self.owner = owner
        self.parameter = parameter
        self.overrides_key = overrides_key

    @override
    def validate(self, param: Param) -> bool:
        # The adapter is an explicit annotation marker. Never widen this to subclass/Optional matching.
        return (
            any(marker is self for marker in param.meta)
            and param.annotation == cast("DependencyKey", self.spec.key).base
        )

    @override
    async def __call__(self, context: Contexts) -> Force:
        key = cast("DependencyKey", self.spec.key)
        if self.overrides_key is not None:
            overrides: Mapping[str, object] = context.get(self.overrides_key, {})
            if self.parameter in overrides:
                return Force(overrides[self.parameter])
        try:
            value = await self.dispatcher.resolve_exact(self.spec, context)
        except ResolutionError as error:
            raise ResolutionError(
                "dependency resolution failed",
                owner=self.owner,
                parameter=self.parameter,
                keys=error.keys if error.keys[:1] == (key,) else (key, *error.keys),
            ) from error
        return Force(value)


class _NativeProvider(Provider[object]):
    native: Provider[object]
    token: object
    key: DependencyKey
    owner: str
    parameter: str
    overrides_key: str | None

    def __init__(
        self,
        native: Provider[object],
        token: object,
        key: DependencyKey,
        owner: str,
        parameter: str,
        overrides_key: str | None,
    ) -> None:
        super().__init__()
        self.native = native
        self.token = token
        self.key = key
        self.owner = owner
        self.parameter = parameter
        self.overrides_key = overrides_key

    @override
    def validate(self, param: Param) -> bool:
        return any(marker is self.token for marker in param.meta) and param.annotation == self.key.base

    @override
    async def __call__(self, context: Contexts) -> object | None:
        if self.overrides_key is not None:
            overrides: Mapping[str, object] = context.get(self.overrides_key, {})
            if self.parameter in overrides:
                return Force(overrides[self.parameter])
        try:
            return await self.native(Contexts(context))
        except Exception as error:
            raise ResolutionError(
                "native provider failed", owner=self.owner, parameter=self.parameter, keys=(self.key,)
            ) from error


def _native_adapter(
    native: Provider[object],
    token: object,
    key: DependencyKey,
    owner: str,
    parameter: str,
    overrides_key: str | None,
) -> Provider[object]:
    priority = native.priority

    class Adapter(_NativeProvider):
        pass

    Adapter.priority = priority
    return Adapter(native, token, key, owner, parameter, overrides_key)


@final
class _DeclineProvider(Provider[object]):
    def __init__(self, token: object, key: DependencyKey, owner: str, parameter: str, priority: int) -> None:
        super().__init__()
        self.token = token
        self.key = key
        self.owner = owner
        self.parameter = parameter
        object.__setattr__(self, "priority", priority)

    @override
    def validate(self, param: Param) -> bool:
        return any(marker is self.token for marker in param.meta) and param.annotation == self.key.base

    @override
    async def __call__(self, context: Contexts) -> object:
        del context
        raise ResolutionError(
            "all native providers declined",
            owner=self.owner,
            parameter=self.parameter,
            keys=(self.key,),
        )


@final
class _OverrideDepend(Depend):
    def __init__(self, target: Factory, cache: bool, context_key: str, parameter: str) -> None:
        super().__init__(target, cache)
        self.context_key = context_key
        self.parameter = parameter

    @override
    def fork(self, provider: list[Provider[object] | ProviderFactory]) -> _OverrideDepend:
        forked = _OverrideDepend(self.target, self.cache, self.context_key, self.parameter)
        forked.sub = Subscriber(self.target, providers=provider)
        return forked

    @override
    async def __call__(self, context: Contexts) -> object:
        # A Depend marker always lives inside a station-signature scope, so the channel is never absent.
        overrides: Mapping[str, object] = context.get(self.context_key, {})
        if self.parameter in overrides:
            return overrides[self.parameter]
        return cast("object", await super().__call__(context))


@final
class PreparedStation[T]:
    """A frozen call site; T is the station's declared return type, not a runtime guarantee.

    Call it after freeze() to execute with injected dependencies. overrides bind only to the
    station's declared signature (its own parameters and local Depends subgraph) and never reach
    provider factories; unknown override names are rejected before execution.
    """

    def __init__(self, dispatcher: DependencyDispatcher, plan: BindingPlan) -> None:
        self._dispatcher = dispatcher
        self.raw_plan = plan

    @property
    def owner(self) -> str:
        """The station callable's stable name (module.qualname), for errors and inspect."""
        return self.raw_plan.owner

    @property
    def needs(self) -> tuple[DependencyKey, ...]:
        """Keys that must be injectable for this station; Depends parameters are excluded."""
        return self.raw_plan.needs

    @property
    def plan(self) -> BindingPlan:
        """The bound plan this station executes; reflects the registry state at the last compile."""
        compiled = self._dispatcher.compiled_plans()
        return compiled.plans.get(id(self), self.raw_plan)

    async def __call__(
        self,
        *,
        overrides: Mapping[str, object] | None = None,
        context: Mapping[str, object] | None = None,
    ) -> T:
        selected = self._dispatcher.station_subscriber(self)
        explicit = dict(overrides or {})
        known = {parameter.name for plan in (self.plan, *self.plan.dependencies) for parameter in plan.parameters}
        unknown = explicit.keys() - known
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ResolutionError(f"unknown overrides: {names}", owner=self.owner)
        call_context = self._dispatcher.call_context(self.plan, explicit, context)
        try:
            # A plain station never attaches propagators, so handle cannot yield ExitState here.
            return cast("T", await selected.handle(call_context))
        except ResolutionError:
            raise
        except Exception as error:
            raise ResolutionError("station execution failed", owner=self.owner) from error


@final
class DependencyDispatcher:
    """Instance-owned DI: registry, immutable plans, aggregated validation, freezing, and calls.

    Lifecycle (ADR 0003): register providers in any order (forward declarations allowed), prepare
    every station, then freeze() once — validation aggregates all problems before any subscriber is
    built. After freeze the registry is closed; the runtime surface is PreparedStation calls and
    resolve() only. Mutations after freeze raise DispatcherFrozenError; execution before freeze
    raises DispatcherNotFrozenError.
    """

    def __init__(
        self,
        *,
        binding_backends: Sequence[BindingBackend] | None = None,
        validation_backend: ValidationBackend | None = None,
    ) -> None:
        """binding_backends default to strict exact-key matching only; native matching is an explicit opt-in."""
        self._binding_backends = (
            tuple(binding_backends) if binding_backends is not None else (ExactKeyBindingBackend(),)
        )
        self._validation_backend = validation_backend or StrictGraphValidationBackend()
        self._providers: list[ProviderSpec] = []
        self._stations: list[PreparedStation[object]] = []
        self._compiled: _Compiled | None = None
        self._subscribers: dict[int, Subscriber[object]] = {}
        self._provider_subscribers: dict[DependencyKey, Subscriber[object]] = {}
        self._specs: dict[DependencyKey, ProviderSpec] = {}
        self._values: dict[DependencyKey, object] = {}
        self._locks: dict[DependencyKey, Lock] = {}
        self._frozen = False
        self.overrides_key = f"courier.overrides.{id(self):x}"

    def _ensure_mutable(self) -> None:
        if self._frozen:
            raise DispatcherFrozenError("dependency dispatcher is frozen")

    def set_binding_backends(self, backends: Sequence[BindingBackend]) -> None:
        """Replace binding backends before freeze(); invalidates compiled plans."""
        self._ensure_mutable()
        self._binding_backends = tuple(backends)
        self._compiled = None

    def set_validation_backend(self, backend: ValidationBackend) -> None:
        """Replace the validation backend before freeze(); replacements keep the same contract."""
        self._ensure_mutable()
        self._validation_backend = backend

    # The key is open vocabulary: a type, an Annotated alias, or a DependencyKey (ADR 0003).
    # Annotated aliases are not assignable to type[T], so a narrower union would lie to callers.
    def register(self, key: object, factory: Factory, *, singleton: bool = True) -> None:
        """Register an exact provider; singletons are constructed once and cached per key.

        The factory plan compiles eagerly: unusable signatures raise SignatureError at registration,
        and duplicate keys raise DuplicateProviderError immediately.
        """
        self._ensure_mutable()
        normalized = key if isinstance(key, DependencyKey) else DependencyKey.of(key)
        if any(provider.key == normalized for provider in self._providers):
            raise DuplicateProviderError(f"duplicate exact provider: {normalized}")
        spec = ProviderSpec.exact(normalized, factory, singleton=singleton)
        self._providers.append(spec)
        self._compiled = None

    @overload
    def provider[F: Factory](self, factory: F, *, singleton: bool = True) -> F: ...

    @overload
    def provider[F: Factory](self, *, singleton: bool = True) -> Callable[[F], F]: ...

    def provider(self, factory: Factory | None = None, *, singleton: bool = True) -> Any:
        """Decorator or direct call: register by the factory's return annotation, type preserved.

        Requires a return annotation (SignatureError otherwise). Equivalent to registering the
        annotated return key directly; use register() when the key differs from the return annotation.
        """

        # The overloads carry F; the implementation can only state the erased runtime shape.
        def decorate(target: Factory) -> Factory:
            hints = get_type_hints(target, include_extras=True)
            if "return" not in hints:
                raise SignatureError(f"provider {target!r} has no return annotation")
            self.register(hints["return"], target, singleton=singleton)
            return target

        return decorate if factory is None else decorate(factory)

    def register_native[T](self, candidate: Provider[T] | ProviderFactory) -> None:
        """Register an arclet native; it participates only behind an explicitly enabled PredicateBindingBackend."""
        self._ensure_mutable()
        self._providers.append(ProviderSpec.from_native(candidate))
        self._compiled = None

    @overload
    def prepare[T](self, target: Callable[..., Coroutine[Any, Any, T]]) -> PreparedStation[T]: ...

    @overload
    def prepare[T](self, target: Callable[..., T]) -> PreparedStation[T]: ...

    def prepare(self, target: Factory) -> PreparedStation[Any]:
        """Compile a station plan without validating; must precede freeze().

        Usable bare as a decorator (@dispatcher.prepare); the returned station keeps owner/needs
        for inspect and refuses execution until the dispatcher is frozen.
        """
        # The overloads carry T; the implementation can only state the erased runtime shape.
        self._ensure_mutable()
        compiled = self.compiled_plans()
        station: PreparedStation[object] = PreparedStation(self, compile_plan(target))
        self._stations.append(station)
        compiled.plans[id(station)] = bind_plan(station.raw_plan, compiled.snapshot, self._binding_backends)
        return station

    def compiled_plans(self) -> _Compiled:
        """Lazily bind the current registry and all stations; invalidated by any mutation."""
        if self._compiled is None:
            snapshot = bind_providers(RegistrySnapshot(tuple(self._providers)), self._binding_backends)
            plans = {
                id(station): bind_plan(station.raw_plan, snapshot, self._binding_backends) for station in self._stations
            }
            self._compiled = _Compiled(snapshot, plans)
            self._specs = {spec.key: spec for spec in snapshot.providers if spec.key is not None}
        return self._compiled

    def validate(self) -> ValidationReport:
        """Aggregate the whole graph's problems in one deterministic report; never calls any factory."""
        compiled = self.compiled_plans()
        return self._validation_backend.validate(compiled.snapshot, tuple(compiled.plans.values()))

    def freeze(self) -> ValidationReport:
        """Validate the whole graph, build all subscribers, then close the registry.

        Single-shot: a second freeze raises DispatcherFrozenError. Raises DependencyValidationError
        with the aggregated report when anything is unsatisfiable; nothing is partially frozen.
        """
        self._ensure_mutable()
        report = self.validate()
        if not report.ok:
            raise DependencyValidationError(report)
        compiled = self.compiled_plans()
        # Overrides bind to the station's declared signature only: provider factories never
        # consume the caller's overrides, so same-named parameters cannot flow implicitly (ADR 0003).
        provider_subscribers = {
            spec.key: self._make_subscriber(spec.plan, overrides_key=None)
            for spec in compiled.snapshot.providers
            if spec.key is not None and spec.plan is not None
        }
        station_subscribers = {
            identity: self._make_subscriber(plan, overrides_key=self.overrides_key)
            for identity, plan in compiled.plans.items()
        }
        self._provider_subscribers = provider_subscribers
        self._subscribers = station_subscribers
        self._frozen = True
        return report

    def _make_subscriber(self, plan: BindingPlan, *, overrides_key: str | None) -> Subscriber[object]:
        graph = {id(item.target): item for item in (plan, *plan.dependencies)}
        providers: list[Provider[object] | ProviderFactory] = []
        annotations: dict[int, dict[str, object]] = {}
        allowed: dict[tuple[int, str], frozenset[int]] = {}

        for item in graph.values():
            hints = get_type_hints(item.target, include_extras=True)
            transformed: dict[str, object] = {}
            for index, parameter in enumerate(item.parameters):
                metadata: list[object] = []
                planned: set[int] = set()
                if parameter.depends is not None:
                    if overrides_key is None:
                        # Unreachable: compile_plan(provider=True) rejects Depends in provider factories
                        # (locked by test_signature_errors_and_provider_depends_are_eager), so a
                        # provider-plan graph never reaches this branch. Fail loudly if that erodes
                        # instead of silently letting provider-side Depends see caller overrides.
                        raise RuntimeError("provider plan parameters cannot carry Depends")
                    dependency = graph[id(parameter.depends.target)]
                    dependency_target = dependency.target
                    marker = _OverrideDepend(dependency_target, parameter.depends.cache, overrides_key, parameter.name)
                    metadata.append(marker)
                else:
                    bindings = item.bindings[index]
                    override_provider = _OverrideProvider(overrides_key, parameter.name)
                    providers.append(override_provider)
                    planned.add(id(override_provider))
                    metadata.append(override_provider)
                    for binding in bindings:
                        if binding.priority is None:
                            adapter = _ExactProvider(self, binding.provider, item.owner, parameter.name, overrides_key)
                            providers.append(adapter)
                            planned.add(id(adapter))
                            metadata.append(adapter)
                        elif binding.native_provider is not None:
                            native_token = object()
                            native_adapter = _native_adapter(
                                binding.native_provider,
                                native_token,
                                parameter.key,
                                item.owner,
                                parameter.name,
                                overrides_key,
                            )
                            providers.append(native_adapter)
                            planned.add(id(native_adapter))
                            metadata.append(native_token)
                    token = object()
                    last_priority = (
                        max((binding.priority or 0 for binding in bindings if binding.priority is not None), default=19)
                        + 1
                    )
                    decline = _DeclineProvider(token, parameter.key, item.owner, parameter.name, last_priority)
                    providers.append(decline)
                    planned.add(id(decline))
                    metadata.append(token)
                allowed[(id(item.target), parameter.name)] = frozenset(planned)
                base = parameter.key.base
                transformed[parameter.name] = Annotated[base, *metadata] if metadata else base
            for name, hint in hints.items():
                if name not in transformed:
                    transformed[name] = hint
            annotations[id(item.target)] = transformed

        wrapped: dict[int, Factory] = {}

        def wrap_plan(item: BindingPlan) -> Factory:
            identity = id(item.target)
            if identity in wrapped:
                return wrapped[identity]

            @wraps(item.target)
            def invoke(*args: object, **kwargs: object) -> object:
                return item.target(*args, **kwargs)

            transformed = annotations[identity]
            for parameter in item.parameters:
                if parameter.depends is None:
                    continue
                dependency = graph[id(parameter.depends.target)]
                dependency_wrapper = wrap_plan(dependency)
                marker = next(
                    marker
                    for marker in get_args(transformed[parameter.name])[1:]
                    if isinstance(marker, _OverrideDepend)
                )
                marker.target = dependency_wrapper
            invoke.__annotations__ = transformed
            signature = inspect.signature(item.target)
            parameters = [
                parameter.replace(annotation=transformed.get(name, parameter.annotation))
                for name, parameter in signature.parameters.items()
            ]
            invoke.__dict__["__signature__"] = signature.replace(parameters=parameters)
            wrapped[identity] = invoke
            return invoke

        root = wrap_plan(plan)
        subscriber = Subscriber(root, providers=providers)
        wrapped_allowed = {(id(wrapped[target]), name): candidates for (target, name), candidates in allowed.items()}
        self._audit_candidates(subscriber, wrapped_allowed, plan.owner)
        return subscriber

    def _audit_candidates(
        self,
        subscriber: Subscriber[object],
        allowed: Mapping[tuple[int, str], frozenset[int]],
        owner: str,
        seen: set[int] | None = None,
    ) -> None:
        visited: set[int] = set() if seen is None else seen
        if id(subscriber) in visited:
            return
        visited.add(id(subscriber))
        issues: list[ValidationIssue] = []
        for parameter in subscriber.params:
            candidates = cast("list[Provider[object]]", parameter.providers)
            expected = allowed.get((id(subscriber.callable_target), parameter.name), frozenset())
            unexpected = [provider for provider in candidates if id(provider) not in expected]
            if unexpected:
                message = f"{owner} parameter {parameter.name!r} received unplanned providers: {unexpected!r}"
                issues.append(ValidationIssue("unexpected_provider", message, owner, parameter.name))
            if parameter.depend is not None:
                self._audit_candidates(parameter.depend.sub, allowed, owner, visited)
        if issues:
            raise DependencyValidationError(ValidationReport(tuple(issues)))

    def station_subscriber(self, station: PreparedStation[object]) -> Subscriber[object]:
        """The execution subscriber of one station; requires freeze()."""
        if not self._frozen:
            raise DispatcherNotFrozenError("freeze the dispatcher before executing a station")
        return self._subscribers[id(station)]

    def call_context(
        self,
        plan: BindingPlan,
        overrides: Mapping[str, object],
        context: Mapping[str, object] | None,
    ) -> Contexts:
        """Build one call's context: strip ambient parameter names, then attach this call's overrides."""
        result = Contexts(context or {})
        parameter_names = {
            parameter.name
            for item in (plan, *plan.dependencies, *(spec.plan for spec in self._specs.values() if spec.plan))
            for parameter in item.parameters
        }
        for name in parameter_names:
            _ = result.pop(name, None)
        result[self.overrides_key] = dict(overrides)
        return result

    # Deliberate open vocabulary, kept as decided in review: Annotated aliases resolve here
    # but infer T as Unknown (they are not assignable to type[T]); typed resolution uses a
    # plain type or an explicit DependencyKey.
    async def resolve[T](self, key: type[T] | DependencyKey | object) -> T:
        """Resolve one exact key outside a station call; requires freeze().

        T follows the key for plain types; singletons are shared, transients construct per call.
        """
        if not self._frozen:
            raise DispatcherNotFrozenError("freeze the dispatcher before resolving dependencies")
        normalized = key if isinstance(key, DependencyKey) else DependencyKey.of(key)
        spec = self._specs.get(normalized)
        if spec is None:
            raise ResolutionError("no exact provider", owner="DependencyDispatcher.resolve", keys=(normalized,))
        try:
            value = await self.resolve_exact(spec, Contexts())
        except ResolutionError as error:
            if normalized in error.keys:
                raise
            raise ResolutionError(
                "dependency resolution failed",
                owner="DependencyDispatcher.resolve",
                keys=(normalized, *error.keys),
            ) from error
        return cast("T", value)

    async def resolve_exact(self, spec: ProviderSpec, context: Contexts) -> object:
        key = cast("DependencyKey", spec.key)
        if not spec.singleton:
            return await self._construct(spec, context)
        if key in self._values:
            return self._values[key]
        lock = self._locks.setdefault(key, Lock())
        async with lock:
            if key in self._values:
                return self._values[key]
            # A process-wide singleton must never retain a call's overrides or native context.
            value = await self._construct(spec, Contexts())
            self._values[key] = value
            return value

    async def _construct(self, spec: ProviderSpec, context: Contexts) -> object:
        key = cast("DependencyKey", spec.key)
        try:
            return await self._provider_subscribers[key].handle(Contexts(context))
        except ResolutionError:
            raise
        except Exception as error:
            raise ResolutionError("provider factory failed", owner=spec.name, keys=(key,)) from error

    def snapshot(self) -> dict[str, dict[str, object]]:
        """Inspect projection of the registry: name -> {singleton, needs}; natives are registration-index-named."""
        result: dict[str, dict[str, object]] = {}
        for index, spec in enumerate(self._providers):
            name = str(spec.key) if spec.key is not None else f"native:{index}:{spec.name}"
            needs = [] if spec.plan is None else [str(key) for key in spec.plan.needs]
            result[name] = {"singleton": spec.singleton, "needs": needs}
        return result
