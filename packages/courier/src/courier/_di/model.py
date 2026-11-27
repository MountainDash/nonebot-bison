import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Self, cast, get_args, get_origin, get_type_hints, override

from arclet.letoderea import Depend, Provider, ProviderFactory


class DIError(Exception):
    """Base class for every dependency-injection error."""


class SignatureError(DIError):
    """A callable's signature cannot serve as a DI plan (missing annotation, or Depends in a provider)."""


class DuplicateProviderError(DIError):
    """The same exact key was registered twice, or a snapshot contains duplicate exact keys."""


type Factory = Callable[..., object]
type Native = Provider[object] | ProviderFactory


def callable_name(target: object) -> str:
    """Best-effort stable name (module.qualname) for error messages and inspect output."""
    module = getattr(target, "__module__", "")
    name = getattr(target, "__qualname__", None) or getattr(target, "__name__", None)
    name = name or type(target).__qualname__
    return f"{module}.{name}" if module else str(name)


@dataclass(frozen=True, slots=True)
class DependencyKey:
    """A normalized dependency key: the base type plus marker objects, excluding Depend markers.

    The open vocabulary is a plain type, an ``Annotated[...]`` alias, or a DependencyKey.
    Base and markers must be hashable: construction rejects unhashable parts eagerly.
    """

    base: object
    markers: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        # Fail fast: keys must be hashable for sets and provider maps (RegistrySnapshot, bindings).
        # The slots dataclass keeps no cached hash; this only rejects unhashable base/markers at construction.
        _ = hash(self)

    @classmethod
    def of(cls, annotation: object) -> Self:
        """Normalize an annotation into a key; Annotated markers are kept, Depend markers are dropped."""
        if get_origin(annotation) is Annotated:
            # typing.get_args and get_type_hints are Any-typed signature boundaries.
            base, *markers = get_args(annotation)
            key = cls(base, tuple(marker for marker in markers if not isinstance(marker, Depend)))
        else:
            key = cls(annotation)
        return key

    @override
    def __str__(self) -> str:
        base = callable_name(self.base) if isinstance(self.base, type) else str(self.base)
        return base if not self.markers else f"{base}[{', '.join(repr(marker) for marker in self.markers)}]"


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """One declared parameter of a plan: its key, default (empty means required), and Depend marker."""

    name: str
    key: DependencyKey
    default: object = inspect.Parameter.empty
    depends: Depend | None = None


@dataclass(frozen=True, slots=True)
class BindingPlan:
    """The immutable plan of one callable: its parameters, per-parameter bindings, and local Depends graph.

    Bindings and validation consume the same plan; nothing about a plan is recomputed per call.
    """

    target: Factory
    parameters: tuple[ParameterSpec, ...]
    owner: str
    bindings: tuple[tuple[Binding, ...], ...] = ()
    dependencies: tuple[BindingPlan, ...] = ()

    @property
    def needs(self) -> tuple[DependencyKey, ...]:
        """Inspect projection: keys of parameters that must be injectable (Depends params excluded)."""
        return tuple(parameter.key for parameter in self.parameters if parameter.depends is None)


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """A registered provider: exact-key factories (with their own compiled plan) or opt-in arclet natives."""

    key: DependencyKey | None
    factory: Factory | None
    plan: BindingPlan | None
    native: Native | None
    name: str
    singleton: bool | None = True

    @classmethod
    def exact(cls, key: object, factory: Factory, *, singleton: bool = True) -> Self:
        """Compile the factory plan eagerly; providers must not use Depends and signatures must be annotated."""
        plan = compile_plan(factory, provider=True)
        normalized = key if isinstance(key, DependencyKey) else DependencyKey.of(key)
        return cls(normalized, factory, plan, None, plan.owner, singleton)

    @classmethod
    def from_native[T](cls, candidate: Provider[T] | ProviderFactory) -> Self:
        """Wrap an arclet Provider/ProviderFactory; it only participates behind PredicateBindingBackend."""
        return cls(None, None, None, cast("Native", candidate), callable_name(type(candidate)), None)


@dataclass(frozen=True, slots=True)
class Binding:
    """One candidate for one parameter. priority=None marks an exact binding; otherwise a native priority."""

    provider: ProviderSpec
    native_provider: Provider[object] | None = None
    priority: int | None = None  # None is exact; arclet native priorities use lower-first ordering.


@dataclass(frozen=True, slots=True)
class RegistrySnapshot:
    """Immutable registry view consumed by binding and validation; duplicate exact keys are rejected."""

    providers: tuple[ProviderSpec, ...] = ()

    def __post_init__(self) -> None:
        seen: set[DependencyKey] = set()
        for provider in self.providers:
            if provider.key is None:
                continue
            if provider.key in seen:
                raise DuplicateProviderError(f"duplicate exact provider: {provider.key}")
            seen.add(provider.key)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One aggregated problem: code in {missing, ambiguous_native, provider_cycle, depends_cycle, ...}."""

    code: str
    message: str
    owner: str
    parameter: str | None = None
    key: DependencyKey | None = None
    cycle: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """The whole validation answer; issues are sorted deterministically, and ok means no issues."""

    issues: tuple[ValidationIssue, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "issues", tuple(sorted(self.issues, key=repr)))

    @property
    def ok(self) -> bool:
        return not self.issues


def compile_plan(target: Factory, *, provider: bool = False) -> BindingPlan:
    """Compile a signature into a plan: parameters need annotations unless defaulted; providers reject Depends.

    Raises SignatureError eagerly for unusable signatures.
    """
    owner = callable_name(target)
    hints = get_type_hints(target, include_extras=True)
    parameters: list[ParameterSpec] = []
    for name, signature_parameter in inspect.signature(target).parameters.items():
        if name not in hints:
            if signature_parameter.default is inspect.Parameter.empty:
                raise SignatureError(f"{owner} parameter {name!r} has no type annotation")
            continue
        markers = get_args(hints[name])[1:] if get_origin(hints[name]) is Annotated else ()
        depends = next((marker for marker in markers if isinstance(marker, Depend)), None)
        if depends is not None and provider:
            raise SignatureError(f"provider {owner} must not use Depends")
        parameters.append(ParameterSpec(name, DependencyKey.of(hints[name]), signature_parameter.default, depends))
    return BindingPlan(target, tuple(parameters), owner)
