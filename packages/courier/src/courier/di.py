"""Public DI facade: instance-owned dependency injection built on arclet-letoderea.

Downstream consumers (bison, dedicated lines) import from here, not from courier._di.
Lifecycle: register in any order, pass every
station through prepare_station(), freeze once with aggregated validation, then run through
PreparedStation calls and resolve() only.
"""

from arclet.letoderea import Depend, Depends, Provider, ProviderFactory

from ._di.binding import BindingBackend, ExactKeyBindingBackend, PredicateBindingBackend
from ._di.dispatcher import DependencyDispatcher, PreparedStation
from ._di.errors import (
    DependencyValidationError,
    DIError,
    DispatcherFrozenError,
    DispatcherNotFrozenError,
    DuplicateProviderError,
    ResolutionError,
    SignatureError,
)
from ._di.model import DependencyKey, ValidationIssue, ValidationReport
from ._di.validation import StrictGraphValidationBackend, ValidationBackend

__all__ = [
    "BindingBackend",
    "DIError",
    "Depend",
    "DependencyDispatcher",
    "DependencyKey",
    "DependencyValidationError",
    "Depends",
    "DispatcherFrozenError",
    "DispatcherNotFrozenError",
    "DuplicateProviderError",
    "ExactKeyBindingBackend",
    "PredicateBindingBackend",
    "PreparedStation",
    "Provider",
    "ProviderFactory",
    "ResolutionError",
    "SignatureError",
    "StrictGraphValidationBackend",
    "ValidationBackend",
    "ValidationIssue",
    "ValidationReport",
]
