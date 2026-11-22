"""Instance-owned dependency injection built on arclet-letoderea."""

from arclet.letoderea import Depend, Depends, Provider, ProviderFactory

from ._di.binding import BindingBackend, ExactKeyBindingBackend, LetodereaPredicateBindingBackend
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
    "LetodereaPredicateBindingBackend",
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
