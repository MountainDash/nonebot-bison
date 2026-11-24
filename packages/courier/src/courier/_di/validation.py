from collections.abc import Callable, Hashable, Sequence
from inspect import Parameter
from typing import Protocol, final

from .model import (
    BindingPlan,
    DependencyKey,
    RegistrySnapshot,
    ValidationIssue,
    ValidationReport,
    callable_name,
)


class ValidationBackend(Protocol):
    """Answer "is the whole declared graph satisfiable". Read-only: never call factories, never touch parcels."""

    def validate(self, snapshot: RegistrySnapshot, plans: Sequence[BindingPlan]) -> ValidationReport: ...


def _cycles[N: Hashable](graph: dict[N, tuple[N, ...]], label: Callable[[N], str]) -> tuple[tuple[N, ...], ...]:
    state: dict[N, int] = {}
    stack: list[N] = []
    found: set[tuple[N, ...]] = set()

    def visit(node: N) -> None:
        state[node] = 1
        stack.append(node)
        for following in sorted(graph[node], key=label):
            if following not in graph:
                continue
            if state.get(following, 0) == 0:
                _ = visit(following)
            elif state[following] == 1:
                loop = stack[stack.index(following) :]
                rotations = [tuple(loop[index:] + loop[:index]) for index in range(len(loop))]
                found.add(min(rotations, key=lambda cycle: tuple(label(node) for node in cycle)))
        _ = stack.pop()
        state[node] = 2

    for node in sorted(graph, key=label):
        if state.get(node, 0) == 0:
            _ = visit(node)
    return tuple(sorted(found, key=lambda cycle: tuple(label(node) for node in cycle)))


@final
class StrictGraphValidationBackend:
    """Structural validation only: a native Provider may still decline at runtime.

    Reports missing bindings (declared defaults never rescue), equal-priority native ambiguity,
    direct/indirect provider cycles, and Depends cycles — aggregated in one deterministic report.
    Replacement backends must keep the same contract, not silently relax it.
    """

    def validate(self, snapshot: RegistrySnapshot, plans: Sequence[BindingPlan]) -> ValidationReport:
        issues: list[ValidationIssue] = []
        all_plans = {id(provider.plan): provider.plan for provider in snapshot.providers if provider.plan is not None}
        for plan in plans:
            for item in (plan, *plan.dependencies):
                all_plans[id(item)] = item

        for plan in all_plans.values():
            for index, parameter in enumerate(plan.parameters):
                if parameter.depends is not None:
                    continue
                candidates = plan.bindings[index] if index < len(plan.bindings) else ()
                if any(binding.priority is None for binding in candidates):
                    continue
                if not candidates:
                    message = f"{plan.owner} parameter {parameter.name!r} needs {parameter.key}"
                    if parameter.default is not Parameter.empty:
                        # Declared defaults never satisfy the dependency graph (ADR 0003).
                        message = f"{message} (declared default does not rescue)"
                    issues.append(ValidationIssue("missing", message, plan.owner, parameter.name, parameter.key))
                    continue
                priorities = [binding.priority for binding in candidates if binding.priority is not None]
                ambiguous = {
                    binding.provider.name
                    for binding in candidates
                    if binding.priority is not None and priorities.count(binding.priority) > 1
                }
                if ambiguous:
                    names = ", ".join(sorted(ambiguous))
                    message = f"{plan.owner} parameter {parameter.name!r} has equal-priority fallbacks: {names}"
                    issues.append(
                        ValidationIssue("ambiguous_native", message, plan.owner, parameter.name, parameter.key)
                    )

        exact = {
            provider.key: provider.plan
            for provider in snapshot.providers
            if provider.key is not None and provider.plan is not None
        }
        provider_graph: dict[DependencyKey, tuple[DependencyKey, ...]] = {}
        for key, plan in exact.items():
            requirements: list[DependencyKey] = []
            for index in range(len(plan.parameters)):
                candidates = plan.bindings[index] if index < len(plan.bindings) else ()
                requirements.extend(
                    binding.provider.key
                    for binding in candidates
                    if binding.priority is None and binding.provider.key is not None
                )
            provider_graph[key] = tuple(requirements)
        for cycle in _cycles(provider_graph, str):
            names = tuple(str(key) for key in (*cycle, cycle[0]))
            message = "provider cycle: " + " -> ".join(names)
            issues.append(ValidationIssue("provider_cycle", message, names[0], cycle=names))

        by_target = {id(plan.target): plan for plan in all_plans.values()}
        depends_graph = {
            identity: tuple(
                id(parameter.depends.target) for parameter in plan.parameters if parameter.depends is not None
            )
            for identity, plan in by_target.items()
        }
        depends_labels = {identity: callable_name(plan.target) for identity, plan in by_target.items()}
        for cycle in _cycles(depends_graph, lambda identity: depends_labels[identity]):
            names = tuple(depends_labels[identity] for identity in (*cycle, cycle[0]))
            message = "Depends cycle: " + " -> ".join(names)
            issues.append(ValidationIssue("depends_cycle", message, names[0], cycle=names))
        return ValidationReport(tuple(issues))
