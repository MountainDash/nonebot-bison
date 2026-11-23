from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from typing import Annotated, final, override

import pytest
from arclet.letoderea import Contexts, Param, Provider, ProviderFactory, provide

from courier._di import (
    Binding,
    BindingBackend,
    BindingPlan,
    DependencyKey,
    Depends,
    DuplicateProviderError,
    ExactKeyBindingBackend,
    ParameterSpec,
    PredicateBindingBackend,
    ProviderSpec,
    RegistrySnapshot,
    SignatureError,
    StrictGraphValidationBackend,
    ValidationReport,
    bind_plan,
    bind_providers,
    compile_plan,
)


@final
class Token:
    pass


@final
class OtherToken:
    pass


@final
class MissingOne:
    pass


@final
class MissingTwo:
    pass


@final
class ForwardA:
    pass


@final
class ForwardB:
    pass


def make_forward_a(_value: ForwardB) -> ForwardA:
    return ForwardA()


def make_forward_b() -> ForwardB:
    return ForwardB()


@final
class CycleA:
    pass


@final
class CycleB:
    pass


@final
class CycleC:
    pass


def make_cycle_a(_value: CycleB) -> CycleA:
    return CycleA()


def make_cycle_b(_value: CycleA) -> CycleB:
    return CycleB()


def make_indirect_a(_value: CycleB) -> CycleA:
    return CycleA()


def make_indirect_b(_value: CycleC) -> CycleB:
    return CycleB()


def make_indirect_c(_value: CycleA) -> CycleC:
    return CycleC()


def depends_self(
    value: Annotated[
        int, Depends(depends_self)  # pyright: ignore[reportUndefinedVariable, reportUnknownArgumentType]
    ],
) -> int:
    return value


def depends_left(
    value: Annotated[
        int, Depends(depends_right)  # pyright: ignore[reportUndefinedVariable, reportUnknownArgumentType]
    ],
) -> int:
    return value


def make_local_other(_value: Token) -> OtherToken:
    return OtherToken()


OTHER_DEFAULT = OtherToken()


def depends_right(value: Annotated[int, Depends(depends_left)]) -> int:
    return value


@final
class TextProvider(Provider[str]):
    priority = 20
    validations: int
    calls: int

    def __init__(self) -> None:
        super().__init__()
        self.validations = 0
        self.calls = 0

    @override
    def validate(self, param: Param) -> bool:
        self.validations += 1
        return param.annotation is str

    @override
    async def __call__(self, context: Contexts) -> str | None:
        self.calls += 1
        return "native"


@final
class TokenProvider(Provider[Token]):
    @override
    async def __call__(self, context: Contexts) -> Token | None:
        return Token()


@final
class TokenProviderFactory(ProviderFactory):
    calls: int
    generated: TokenProvider | None

    def __init__(self) -> None:
        self.calls = 0
        self.generated = None

    @override
    def validate(self, param: Param) -> TokenProvider | None:
        self.calls += 1
        if param.annotation is not Token:
            return None
        self.generated = TokenProvider()
        return self.generated


def _bind_graph(
    snapshot: RegistrySnapshot,
    roots: Sequence[BindingPlan],
    backends: Sequence[BindingBackend] | None = None,
) -> tuple[RegistrySnapshot, tuple[BindingPlan, ...]]:
    bound = bind_providers(snapshot, backends)
    return bound, tuple(bind_plan(root, bound, backends) for root in roots)


def _validate(
    snapshot: RegistrySnapshot,
    *roots: BindingPlan,
    backends: Sequence[BindingBackend] | None = None,
) -> ValidationReport:
    bound, plans = _bind_graph(snapshot, roots, backends)
    return StrictGraphValidationBackend().validate(bound, plans)


def test_exact_keys_and_annotated_markers_are_distinct() -> None:
    plain = ProviderSpec.exact(str, lambda: "plain")
    marked = ProviderSpec.exact(Annotated[str, "tenant"], lambda: "marked")
    snapshot = RegistrySnapshot((plain, marked))

    def root(_plain_value: str, _marked_value: Annotated[str, "tenant"]) -> None:
        pass

    bound, plans = _bind_graph(snapshot, (compile_plan(root),))
    report = StrictGraphValidationBackend().validate(bound, plans)

    assert report.ok
    assert plans[0].bindings[0][0].provider.key == DependencyKey.of(str)
    assert plans[0].bindings[1][0].provider.key == DependencyKey.of(Annotated[str, "tenant"])


@pytest.mark.parametrize("annotation", [str, Annotated[str, "tenant"]])
def test_plain_and_marked_keys_never_fall_back_to_each_other(annotation: object) -> None:
    registered = Annotated[str, "tenant"] if annotation is str else str
    snapshot = RegistrySnapshot((ProviderSpec.exact(registered, lambda: "value"),))

    def plain_root(_value: str) -> None:
        pass

    def marked_root(_value: Annotated[str, "tenant"]) -> None:
        pass

    root = plain_root if annotation is str else marked_root
    report = _validate(snapshot, compile_plan(root))

    assert [issue.code for issue in report.issues] == ["missing"]
    assert report.issues[0].key == DependencyKey.of(annotation)


def test_dependency_key_rejects_unhashable_parts_at_construction() -> None:
    with pytest.raises(TypeError):
        _ = DependencyKey(["unhashable"])
    with pytest.raises(TypeError):
        _ = DependencyKey.of(Annotated[int, ["unhashable"]])


def test_duplicate_exact_key_is_rejected_and_snapshot_is_frozen() -> None:
    provider = ProviderSpec.exact(Token, Token)
    with pytest.raises(DuplicateProviderError):
        _ = RegistrySnapshot((provider, provider))

    snapshot = RegistrySnapshot((provider,))
    attribute = "providers"
    with pytest.raises(FrozenInstanceError):
        setattr(snapshot, attribute, ())
    extended = RegistrySnapshot((*snapshot.providers, ProviderSpec.exact(OtherToken, OtherToken)))
    assert len(extended.providers) == 2
    assert len(snapshot.providers) == 1


def test_native_provider_is_validated_once_and_never_called_by_validation() -> None:
    native = TextProvider()
    snapshot = RegistrySnapshot((ProviderSpec.from_native(native),))

    def root(_value: str) -> None:
        pass

    assert [issue.code for issue in _validate(snapshot, compile_plan(root)).issues] == ["missing"]
    assert native.validations == 0
    report = _validate(snapshot, compile_plan(root), backends=(PredicateBindingBackend(),))

    assert report.ok
    assert native.validations == 1
    assert native.calls == 0


def test_native_provider_factory_generates_one_saved_provider() -> None:
    factory = TokenProviderFactory()
    snapshot = RegistrySnapshot((ProviderSpec.from_native(factory),))

    def root(_value: Token) -> None:
        pass

    bound, plans = _bind_graph(snapshot, (compile_plan(root),), (PredicateBindingBackend(),))
    binding = plans[0].bindings[0][0]
    report = StrictGraphValidationBackend().validate(bound, plans)

    assert report.ok
    assert factory.calls == 1
    assert binding.native_provider is factory.generated


def test_string_marker_does_not_create_a_context_key_provider() -> None:
    native = TextProvider()
    backend = PredicateBindingBackend()
    snapshot = RegistrySnapshot((ProviderSpec.from_native(native),))

    def root(_value: Annotated[str, "tenant"]) -> None:
        pass

    plan = compile_plan(root)
    bindings = backend.bind(plan.parameters[0], snapshot)

    assert len(bindings) == 1
    assert bindings[0].native_provider is native
    assert plan.parameters[0].key.markers == ("tenant",)


def test_same_priority_native_candidates_are_ambiguous() -> None:
    snapshot = RegistrySnapshot((ProviderSpec.from_native(TextProvider()), ProviderSpec.from_native(TextProvider())))

    def root(_value: str) -> None:
        pass

    report = _validate(snapshot, compile_plan(root), backends=(PredicateBindingBackend(),))

    assert [issue.code for issue in report.issues] == ["ambiguous_native"]


def test_equal_priority_fallbacks_are_ambiguous_even_behind_a_unique_winner() -> None:
    first = provide(str, call=lambda _context: "first", priority=0)
    fallback_one = provide(str, call=lambda _context: "fallback-one", priority=10)
    fallback_two = provide(str, call=lambda _context: "fallback-two", priority=10)
    snapshot = RegistrySnapshot(tuple(ProviderSpec.from_native(item) for item in (first, fallback_one, fallback_two)))

    def root(_value: str) -> None:
        pass

    report = _validate(snapshot, compile_plan(root), backends=(PredicateBindingBackend(),))

    assert [issue.code for issue in report.issues] == ["ambiguous_native"]


def test_out_of_order_forward_declarations_bind() -> None:
    snapshot = RegistrySnapshot(
        (ProviderSpec.exact(ForwardA, make_forward_a), ProviderSpec.exact(ForwardB, make_forward_b))
    )

    def root(_value: ForwardA) -> None:
        pass

    assert _validate(snapshot, compile_plan(root)).ok


def test_multiple_missing_needs_are_aggregated_and_sorted() -> None:
    def root(_z: MissingTwo, _a: MissingOne) -> None:
        pass

    report = _validate(RegistrySnapshot(), compile_plan(root))

    assert [issue.code for issue in report.issues] == ["missing", "missing"]
    assert [issue.parameter for issue in report.issues] == ["_a", "_z"]
    assert report == _validate(RegistrySnapshot(), compile_plan(root))


def test_provider_factory_transitive_missing_is_reported_even_when_unused() -> None:
    def needs_missing(_value: MissingOne) -> ForwardB:
        return ForwardB()

    snapshot = RegistrySnapshot(
        (ProviderSpec.exact(ForwardA, make_forward_a), ProviderSpec.exact(ForwardB, needs_missing))
    )

    report = _validate(snapshot)

    assert [issue.code for issue in report.issues] == ["missing"]
    assert report.issues[0].owner.endswith("needs_missing")
    assert report.issues[0].key == DependencyKey.of(MissingOne)


def test_direct_provider_cycle_is_reported() -> None:
    def self_provider(value: CycleA) -> CycleA:
        return value

    report = _validate(RegistrySnapshot((ProviderSpec.exact(CycleA, self_provider),)))

    assert [issue.code for issue in report.issues] == ["provider_cycle"]
    assert report.issues[0].cycle[0] == report.issues[0].cycle[-1]


def test_indirect_provider_cycles_are_reported() -> None:
    direct = RegistrySnapshot((ProviderSpec.exact(CycleA, make_cycle_a), ProviderSpec.exact(CycleB, make_cycle_b)))
    indirect = RegistrySnapshot(
        (
            ProviderSpec.exact(CycleA, make_indirect_a),
            ProviderSpec.exact(CycleB, make_indirect_b),
            ProviderSpec.exact(CycleC, make_indirect_c),
        )
    )

    for snapshot in (direct, indirect):
        report = _validate(snapshot)
        assert [issue.code for issue in report.issues] == ["provider_cycle"]


def test_direct_and_indirect_depends_cycles_are_reported() -> None:
    def direct(_value: Annotated[int, Depends(depends_self)]) -> None:
        pass

    def indirect(_value: Annotated[int, Depends(depends_left)]) -> None:
        pass

    for root, cycle_length in ((direct, 2), (indirect, 3)):
        report = _validate(RegistrySnapshot(), compile_plan(root))
        assert [issue.code for issue in report.issues] == ["depends_cycle"]
        assert len(report.issues[0].cycle) == cycle_length


def test_diamond_is_not_a_cycle() -> None:
    def make_d() -> Token:
        return Token()

    def make_b(_value: Token) -> CycleB:
        return CycleB()

    def make_c(_value: Token) -> CycleC:
        return CycleC()

    def make_a(_left: CycleB, _right: CycleC) -> CycleA:
        return CycleA()

    snapshot = RegistrySnapshot(
        (
            ProviderSpec.exact(Token, make_d),
            ProviderSpec.exact(CycleB, make_b),
            ProviderSpec.exact(CycleC, make_c),
            ProviderSpec.exact(CycleA, make_a),
        )
    )

    assert _validate(snapshot).ok


def test_needs_match_signature_semantics_before_and_after_binding() -> None:
    def root(
        _required: Annotated[str, "tenant"] = "still required",
        _ignored=42,  # pyright: ignore[reportMissingParameterType]
        _local_value: Annotated[OtherToken, Depends(make_local_other)] = OTHER_DEFAULT,
    ) -> None:
        pass

    unbound = compile_plan(root)
    snapshot = RegistrySnapshot((ProviderSpec.exact(Annotated[str, "tenant"], lambda: "value"),))
    bound, plans = _bind_graph(snapshot, (unbound,))

    assert unbound.needs == plans[0].needs == (DependencyKey.of(Annotated[str, "tenant"]),)
    assert [parameter.name for parameter in plans[0].parameters] == ["_required", "_local_value"]
    assert plans[0].dependencies[0].needs == (DependencyKey.of(Token),)
    report = StrictGraphValidationBackend().validate(bound, plans)
    assert [issue.key for issue in report.issues] == [DependencyKey.of(Token)]


def test_signature_errors_and_provider_depends_are_eager() -> None:
    def missing_annotation(_value) -> None:  # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
        pass

    def invalid_provider(_value: Annotated[Token, Depends(Token)]) -> OtherToken:
        return OtherToken()

    with pytest.raises(SignatureError):
        _ = compile_plan(missing_annotation)  # pyright: ignore[reportUnknownArgumentType]
    with pytest.raises(SignatureError, match="must not use Depends"):
        _ = ProviderSpec.exact(OtherToken, invalid_provider)


def test_validation_never_invokes_exact_factories() -> None:
    calls: list[str] = []

    def token_factory() -> Token:
        calls.append("token")
        return Token()

    def other_factory(_token: Token) -> OtherToken:
        calls.append("other")
        return OtherToken()

    def root(_value: OtherToken) -> None:
        pass

    snapshot = RegistrySnapshot(
        (ProviderSpec.exact(Token, token_factory), ProviderSpec.exact(OtherToken, other_factory))
    )
    assert _validate(snapshot, compile_plan(root)).ok
    assert calls == []


@final
class NoBindings:
    def bind(self, parameter: ParameterSpec, snapshot: RegistrySnapshot) -> tuple[Binding, ...]:
        del parameter, snapshot
        return ()


@final
class IndependentValidation:
    def validate(self, snapshot: RegistrySnapshot, plans: Sequence[BindingPlan]) -> ValidationReport:
        del snapshot, plans
        return ValidationReport()


def test_custom_binding_and_validation_backends_are_independent() -> None:
    def root(_value: Token) -> None:
        pass

    snapshot = RegistrySnapshot((ProviderSpec.exact(Token, Token),))
    bound, plans = _bind_graph(snapshot, (compile_plan(root),), (NoBindings(),))
    assert [issue.code for issue in StrictGraphValidationBackend().validate(bound, plans).issues] == ["missing"]
    assert IndependentValidation().validate(bound, plans).ok

    exact_bound, exact_plans = _bind_graph(snapshot, (compile_plan(root),), (ExactKeyBindingBackend(),))
    assert StrictGraphValidationBackend().validate(exact_bound, exact_plans).ok
