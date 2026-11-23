import asyncio
import subprocess
import sys
from collections.abc import Sequence
from typing import Annotated, cast, final, override

import pytest
from arclet.letoderea import Contexts, Param, Provider, ProviderFactory, global_providers, provide  # pyright: ignore[reportUnknownVariableType]

from courier._di import BindingPlan, RegistrySnapshot
from courier.di import (
    DependencyDispatcher,
    DependencyKey,
    DependencyValidationError,
    Depends,
    DispatcherFrozenError,
    DispatcherNotFrozenError,
    DuplicateProviderError,
    ExactKeyBindingBackend,
    PredicateBindingBackend,
    ResolutionError,
    ValidationReport,
)


@final
class Token:
    pass


@final
class OtherToken:
    pass


@final
class Box:
    token: Token

    def __init__(self, token: Token) -> None:
        self.token = token


def make_token() -> Token:
    return Token()


def make_box(token: Token) -> Box:
    return Box(token)


def depends_cycle(
    value: Annotated[int, Depends(depends_cycle)],  # pyright: ignore[reportUndefinedVariable, reportUnknownArgumentType]
) -> int:
    return value


async def test_forward_registration_sync_async_and_duplicate() -> None:
    dispatcher = DependencyDispatcher()
    dispatcher.register(Box, make_box)

    @dispatcher.provider
    async def token() -> Token:
        return Token()

    with pytest.raises(DuplicateProviderError):
        dispatcher.register(Token, make_token)

    assert dispatcher.validate().ok
    _ = dispatcher.freeze()
    box = await dispatcher.resolve(Box)
    assert box.token is await dispatcher.resolve(Token)


async def test_prepare_does_not_validate_and_freeze_aggregates_without_calling_factories() -> None:
    calls: list[str] = []
    dispatcher = DependencyDispatcher()

    def token_factory(_missing: OtherToken) -> Token:
        calls.append("token")
        return Token()

    def station(_token: Token, _missing: str) -> None:
        pass

    dispatcher.register(Token, token_factory)
    prepared = dispatcher.prepare(station)
    assert prepared.needs == (DependencyKey.of(Token), DependencyKey.of(str))
    report = dispatcher.validate()
    assert {issue.code for issue in report.issues} == {"missing"}
    assert len(report.issues) == 2
    assert calls == []
    with pytest.raises(DependencyValidationError) as caught:
        _ = dispatcher.freeze()
    assert caught.value.report == report
    assert calls == []


async def test_cycles_are_validation_errors_not_recursion_errors() -> None:
    dispatcher = DependencyDispatcher()

    def first(_value: OtherToken) -> Token:
        return Token()

    def second(_value: Token) -> OtherToken:
        return OtherToken()

    dispatcher.register(Token, first)
    dispatcher.register(OtherToken, second)
    with pytest.raises(DependencyValidationError) as caught:
        _ = dispatcher.freeze()
    assert [issue.code for issue in caught.value.report.issues] == ["provider_cycle"]


async def test_exact_annotated_keys_and_none_values() -> None:
    dispatcher = DependencyDispatcher()
    dispatcher.register(str, lambda: "plain")
    dispatcher.register(Annotated[str, "tenant"], lambda: None)
    _ = dispatcher.freeze()

    assert await dispatcher.resolve(str) == "plain"
    assert await dispatcher.resolve(Annotated[str, "tenant"]) is None


async def test_prepare_must_precede_freeze_and_none_reaches_station() -> None:
    dispatcher = DependencyDispatcher()
    dispatcher.register(Annotated[str, "tenant"], lambda: None)

    async def station(value: Annotated[str, "tenant"]) -> object:
        return value

    prepared = dispatcher.prepare(station)
    with pytest.raises(DispatcherNotFrozenError):
        _ = await prepared()
    _ = dispatcher.freeze()
    assert await prepared() is None
    with pytest.raises(DispatcherFrozenError):
        _ = dispatcher.prepare(station)


@final
class TextProvider(Provider[str]):
    calls: int

    def __init__(self, value: str | None = "native") -> None:
        super().__init__()
        self.value = value
        self.calls = 0

    @override
    def validate(self, param: Param) -> bool:
        return cast("object", param.annotation) is str

    @override
    async def __call__(self, context: Contexts) -> str | None:
        self.calls += 1
        return self.value


@final
class TokenProvider(Provider[Token]):
    @override
    async def __call__(self, context: Contexts) -> Token:
        return Token()


@final
class TokenProviderFactory(ProviderFactory):
    calls: int

    def __init__(self) -> None:
        self.calls = 0

    @override
    def validate(self, param: Param) -> TokenProvider | None:
        self.calls += 1
        return TokenProvider() if cast("object", param.annotation) is Token else None


@final
class MarkerProvider(Provider[Token]):
    def __init__(self, marker: str, value: Token) -> None:
        super().__init__()
        self.marker = marker
        self.value = value

    @override
    def validate(self, param: Param) -> bool:
        return self.marker in param.meta

    @override
    async def __call__(self, context: Contexts) -> Token:
        return self.value


@final
class MarkerProviderFactory(ProviderFactory):
    def __init__(self, marker: str, value: Token) -> None:
        self.marker = marker
        self.value = value

    @override
    def validate(self, param: Param) -> MarkerProvider | None:
        return MarkerProvider(self.marker, self.value) if self.marker in param.meta else None


def native_dispatcher() -> DependencyDispatcher:
    return DependencyDispatcher(binding_backends=(ExactKeyBindingBackend(), PredicateBindingBackend()))


async def test_native_is_opt_in_exact_wins_and_none_declines() -> None:
    def station(value: str) -> str:
        return value

    strict = DependencyDispatcher()
    native = TextProvider()
    strict.register_native(native)
    _ = strict.prepare(station)
    assert [issue.code for issue in strict.validate().issues] == ["missing"]

    dispatcher = native_dispatcher()
    dispatcher.register_native(native)
    dispatcher.register(str, lambda: "exact")
    prepared = dispatcher.prepare(station)
    _ = dispatcher.freeze()
    assert await prepared() == "exact"
    assert native.calls == 0
    native_snapshot = next(value for key, value in dispatcher.snapshot().items() if key.startswith("native:"))
    assert native_snapshot["singleton"] is None


async def test_native_none_decline_reports_station_parameter() -> None:
    dispatcher = native_dispatcher()
    dispatcher.register_native(TextProvider(None))

    def station(value: str) -> str:
        return value

    prepared = dispatcher.prepare(station)
    _ = dispatcher.freeze()
    with pytest.raises(ResolutionError) as caught:
        _ = await prepared()
    assert caught.value.parameter == "value"
    assert caught.value.keys == (DependencyKey.of(str),)


async def test_native_factory_is_generated_once_across_validation_and_freeze() -> None:
    dispatcher = native_dispatcher()
    factory = TokenProviderFactory()
    dispatcher.register_native(factory)

    def station(value: Token) -> Token:
        return value

    prepared = dispatcher.prepare(station)
    assert dispatcher.validate().ok
    assert dispatcher.validate().ok
    _ = dispatcher.freeze()
    assert isinstance(await prepared(), Token)
    assert isinstance(await prepared(), Token)
    assert factory.calls == 1


async def test_native_marker_bindings_are_exactly_what_execution_uses() -> None:
    dispatcher = native_dispatcher()
    tenant_value = Token()
    other_value = Token()
    dispatcher.register_native(MarkerProvider("tenant", tenant_value))
    dispatcher.register_native(MarkerProviderFactory("other", other_value))

    def station(tenant: Annotated[Token, "tenant"], other: Annotated[Token, "other"]) -> tuple[Token, Token]:
        return tenant, other

    prepared = dispatcher.prepare(station)
    assert all(len(binding) == 1 for binding in prepared.plan.bindings)
    assert dispatcher.validate().ok
    _ = dispatcher.freeze()
    assert await prepared() == (tenant_value, other_value)


async def test_equal_priority_native_candidates_fail_before_execution() -> None:
    dispatcher = native_dispatcher()
    dispatcher.register_native(TextProvider("one"))
    dispatcher.register_native(TextProvider("two"))

    def station(value: str) -> str:
        return value

    _ = dispatcher.prepare(station)
    with pytest.raises(DependencyValidationError) as caught:
        _ = dispatcher.freeze()
    assert [issue.code for issue in caught.value.report.issues] == ["ambiguous_native"]


async def test_explicit_overrides_and_no_ambient_name_shadow() -> None:
    dispatcher = DependencyDispatcher()
    token = Token()
    dispatcher.register(Token, lambda: token)

    def station(value: Token) -> Token:
        return value

    prepared = dispatcher.prepare(station)
    _ = dispatcher.freeze()
    override = Token()
    assert await prepared(overrides={"value": override}) is override
    assert await prepared(overrides={"value": None}) is None
    assert await prepared(context={"value": override}) is token
    with pytest.raises(ResolutionError, match="unknown overrides"):
        _ = await prepared(overrides={"typo": override})


async def test_override_wins_after_cached_resolution_and_does_not_stick() -> None:
    dispatcher = DependencyDispatcher()
    registered = Token()
    dispatcher.register(Token, lambda: registered)

    def station(value: Token) -> Token:
        return value

    prepared = dispatcher.prepare(station)
    _ = dispatcher.freeze()
    override = Token()
    assert await prepared() is registered
    assert await prepared(overrides={"value": override}) is override
    assert await prepared() is registered


async def test_override_wins_when_another_call_records_provider_first() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    slow_calls = 0

    async def slow_factory() -> OtherToken:
        nonlocal slow_calls
        slow_calls += 1
        if slow_calls == 1:
            started.set()
            _ = await release.wait()
        return OtherToken()

    dispatcher = DependencyDispatcher()
    registered = Token()
    dispatcher.register(Token, lambda: registered)
    dispatcher.register(OtherToken, slow_factory, singleton=False)

    async def station(_slow: OtherToken, value: Token) -> Token:
        return value

    prepared = dispatcher.prepare(station)
    _ = dispatcher.freeze()
    override = Token()
    pending = asyncio.create_task(prepared(overrides={"value": override}))
    _ = await started.wait()
    assert await prepared() is registered
    release.set()
    assert await pending is override


async def test_global_provider_cannot_steal_an_exact_key() -> None:
    hostile = provide(str, call=lambda _context: "hostile")
    providers = cast("list[object]", global_providers)
    providers.append(hostile)
    try:
        dispatcher = DependencyDispatcher()
        dispatcher.register(str, lambda: "registered")

        def station(value: str) -> str:
            return value

        prepared = dispatcher.prepare(station)
        _ = dispatcher.freeze()
        assert await prepared(context={"other": "context"}) == "registered"
        assert hostile in providers
    finally:
        providers.remove(hostile)


async def test_unplanned_callable_provider_fails_candidate_audit() -> None:
    hostile = provide(str, call=lambda _context: "hostile")

    def station(value: str) -> str:
        return value

    station.__dict__["__providers__"] = [hostile]
    dispatcher = DependencyDispatcher()
    dispatcher.register(str, lambda: "registered")
    _ = dispatcher.prepare(station)
    with pytest.raises(DependencyValidationError) as caught:
        _ = dispatcher.freeze()
    assert [issue.code for issue in caught.value.report.issues] == ["unexpected_provider"]


async def test_singleton_is_shared_transient_is_not_and_override_is_not_captured() -> None:
    dispatcher = DependencyDispatcher()
    calls = 0
    registered = Token()

    def token_factory() -> Token:
        nonlocal calls
        calls += 1
        return registered

    dispatcher.register(Token, token_factory)
    dispatcher.register(Box, make_box)
    dispatcher.register(OtherToken, OtherToken, singleton=False)

    def first(value: Token, box: Box) -> tuple[Token, Box]:
        return value, box

    def second(value: Token) -> Token:
        return value

    one = dispatcher.prepare(first)
    two = dispatcher.prepare(second)
    _ = dispatcher.freeze()
    override = Token()
    first_value, box = cast("tuple[Token, Box]", await one(overrides={"value": override}))
    assert first_value is override
    assert box.token is registered
    assert await two() is registered
    assert await dispatcher.resolve(Token) is registered
    assert calls == 1
    assert await dispatcher.resolve(OtherToken) is not await dispatcher.resolve(OtherToken)


async def test_transient_provider_does_not_clear_later_override() -> None:
    dispatcher = DependencyDispatcher()
    registered = OtherToken()
    dispatcher.register(Token, Token, singleton=False)
    dispatcher.register(OtherToken, lambda: registered)

    def station(_first: Token, second: OtherToken) -> OtherToken:
        return second

    prepared = dispatcher.prepare(station)
    _ = dispatcher.freeze()
    override = OtherToken()
    assert await prepared(overrides={"second": override}) is override


async def test_native_context_writes_cannot_steal_later_exact_keys() -> None:
    injected = OtherToken()

    class ContextWriter(Provider[Token]):
        @override
        async def __call__(self, context: Contexts) -> Token:
            context["second"] = injected
            return Token()

    dispatcher = native_dispatcher()
    registered = OtherToken()
    dispatcher.register_native(ContextWriter())
    dispatcher.register(OtherToken, lambda: registered)

    def station(_first: Token, second: OtherToken) -> OtherToken:
        return second

    prepared = dispatcher.prepare(station)
    _ = dispatcher.freeze()
    assert await prepared() is registered


async def test_async_singleton_single_flight_and_failure_retry() -> None:
    dispatcher = DependencyDispatcher()
    calls = 0

    async def token_factory() -> Token:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return Token()

    dispatcher.register(Token, token_factory)
    _ = dispatcher.freeze()
    values = await asyncio.gather(*(dispatcher.resolve(Token) for _ in range(12)))
    assert calls == 1
    assert all(value is values[0] for value in values)

    failing = DependencyDispatcher()
    attempts = 0

    def unreliable() -> Token:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ValueError("try again")
        return Token()

    failing.register(Token, unreliable)
    _ = failing.freeze()
    with pytest.raises(ResolutionError) as caught:
        _ = await failing.resolve(Token)
    assert has_cause(caught.value, ValueError)
    assert isinstance(await failing.resolve(Token), Token)
    assert attempts == 2


async def test_cancellation_propagates_and_does_not_publish_a_singleton() -> None:
    dispatcher = DependencyDispatcher()
    attempts = 0

    async def token_factory() -> Token:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise asyncio.CancelledError
        return Token()

    dispatcher.register(Token, token_factory)
    _ = dispatcher.freeze()
    with pytest.raises(asyncio.CancelledError):
        _ = await dispatcher.resolve(Token)
    assert isinstance(await dispatcher.resolve(Token), Token)
    assert attempts == 2


def has_cause(error: BaseException, kind: type[BaseException]) -> bool:
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, kind):
            return True
        current = current.__cause__
    return False


async def test_depends_local_derivation_override_and_cycle() -> None:
    dispatcher = DependencyDispatcher()

    def station(value: Annotated[Box, Depends(make_box)]) -> Box:
        return value

    prepared = dispatcher.prepare(station)
    with pytest.raises(DependencyValidationError):
        _ = dispatcher.freeze()

    dispatcher = DependencyDispatcher()
    dispatcher.register(Token, make_token)
    prepared = dispatcher.prepare(station)
    _ = dispatcher.freeze()
    assert isinstance(await prepared(), Box)
    override = Box(Token())
    assert await prepared(overrides={"value": override}) is override


async def test_depends_cycle_is_aggregated_before_subscriber_construction() -> None:
    dispatcher = DependencyDispatcher()

    def station(value: Annotated[int, Depends(depends_cycle)]) -> int:
        return value

    _ = dispatcher.prepare(station)
    with pytest.raises(DependencyValidationError) as caught:
        _ = dispatcher.freeze()
    assert [issue.code for issue in caught.value.report.issues] == ["depends_cycle"]


async def test_validation_backend_is_not_called_at_runtime_and_mutation_freezes() -> None:
    @final
    class CountingValidation:
        calls: int = 0

        def validate(self, snapshot: RegistrySnapshot, plans: Sequence[BindingPlan]) -> ValidationReport:
            del snapshot, plans
            self.calls += 1
            return ValidationReport()

    validator = CountingValidation()
    dispatcher = DependencyDispatcher(validation_backend=validator)
    dispatcher.register(Token, make_token)

    def station(value: Token) -> Token:
        return value

    prepared = dispatcher.prepare(station)
    assert validator.calls == 0
    _ = dispatcher.freeze()
    assert validator.calls == 1
    _ = await prepared()
    _ = await dispatcher.resolve(Token)
    assert validator.calls == 1
    with pytest.raises(DispatcherFrozenError):
        dispatcher.register_native(TextProvider())
    with pytest.raises(DispatcherFrozenError):
        dispatcher.set_binding_backends((ExactKeyBindingBackend(),))
    with pytest.raises(DispatcherFrozenError):
        dispatcher.set_validation_backend(validator)
    with pytest.raises(DispatcherFrozenError):
        dispatcher.register(Token, make_token)


async def test_snapshot_needs_and_station_failure_cause() -> None:
    dispatcher = DependencyDispatcher()
    dispatcher.register(Token, make_token)
    dispatcher.register(Box, make_box)

    def station(_box: Box) -> None:
        raise ValueError("station failed")

    prepared = dispatcher.prepare(station)
    _ = dispatcher.freeze()
    snapshot = dispatcher.snapshot()
    assert snapshot[str(DependencyKey.of(Token))] == {"singleton": True, "needs": []}
    assert snapshot[str(DependencyKey.of(Box))] == {"singleton": True, "needs": [str(DependencyKey.of(Token))]}
    assert prepared.needs == (DependencyKey.of(Box),)
    with pytest.raises(ResolutionError) as caught:
        _ = await prepared()
    assert caught.value.owner.endswith("station")
    assert has_cause(caught.value, ValueError)


def test_clean_import_has_no_host_frameworks() -> None:
    code = """
import sys
import courier.di
forbidden = ('nonebot', 'entari', 'launart', 'satori')
loaded = [name for name in sys.modules if name.lower().startswith(forbidden)]
assert not loaded, loaded
"""
    _ = subprocess.run([sys.executable, "-c", code], check=True)
