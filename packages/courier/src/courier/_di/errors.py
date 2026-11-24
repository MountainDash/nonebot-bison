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
    """freeze() refused to start: the aggregated ValidationReport is attached as .report."""

    report: ValidationReport

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        details = "\n".join(f"- {issue.message}" for issue in report.issues)
        super().__init__(f"dependency validation failed:\n{details}")


@final
class DispatcherFrozenError(DIError):
    """A mutation (register/prepare/replace backends/freeze again) was attempted after freeze()."""


@final
class DispatcherNotFrozenError(DIError):
    """An execution entry point (station call, resolve) was attempted before freeze()."""


@final
class ResolutionError(DIError):
    """A runtime dependency could not be produced; carries owner, parameter, and the failing key chain."""

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
