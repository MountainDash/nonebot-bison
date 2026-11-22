from __future__ import annotations

from typing import final

from .model import DependencyKey, DIError, DuplicateProviderError, SignatureError, ValidationReport

__all__ = [
    "DIError",
    "DependencyValidationError",
    "DispatcherFrozenError",
    "DispatcherNotFrozenError",
    "DuplicateProviderError",
    "ResolutionError",
    "SignatureError",
]


@final
class DependencyValidationError(DIError):
    report: ValidationReport

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        details = "\n".join(f"- {issue.message}" for issue in report.issues)
        super().__init__(f"dependency validation failed:\n{details}")


@final
class DispatcherFrozenError(DIError): ...


@final
class DispatcherNotFrozenError(DIError): ...


@final
class ResolutionError(DIError):
    owner: str
    parameter: str | None
    keys: tuple[DependencyKey, ...]

    def __init__(
        self,
        message: str,
        *,
        owner: str,
        parameter: str | None = None,
        keys: tuple[DependencyKey, ...] = (),
    ) -> None:
        self.owner = owner
        self.parameter = parameter
        self.keys = keys
        location = owner if parameter is None else f"{owner} parameter {parameter!r}"
        chain = " -> ".join(str(key) for key in keys) if keys else "<none>"
        super().__init__(f"{message}; location={location}; key chain={chain}")
