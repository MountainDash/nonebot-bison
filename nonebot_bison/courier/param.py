from collections.abc import Callable
from dataclasses import dataclass
import inspect
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Self,
    cast,
    get_args,
    get_origin,
    override,
)
from typing_extensions import Sentinel

from nonebot.compat import FieldInfo, ModelField
from nonebot.dependencies import Param
from nonebot.dependencies.utils import check_field_type
from nonebot.internal.params import DependencyCache as DependencyCache
from nonebot.internal.params import DependsInner as DependsInner
from nonebot.params import DefaultParam as DefaultParam
from nonebot.params import DependParam as DependParam
from nonebot.params import Depends as Depends
from nonebot.typing import origin_is_annotated
from nonebot.utils import generic_check_issubclass

from .parcel import DeliveryReceipt, Parcel
from .types import _DEAD_REASON_FLAG, _METADATA_FLAG


class ParcelParam(Param):
    """`courier.Parcel` 注入参数

    解析所有类型为且仅为`courier.Parcel` 及其子类或 `None`，以及名为 `parcel` 且没有类型注解的参数。
    """

    KEYWORD: Literal["parcel"] = "parcel"

    def __init__(self, *args, checker: ModelField | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.checker = checker

    def __repr__(self) -> str:
        return "ParcelParam(" + (repr(self.checker.annotation) if self.checker is not None else "") + ")"

    @classmethod
    @override
    def _check_param(cls, param: inspect.Parameter, allow_types: tuple[type[Param], ...]) -> Self | None:
        # param type is Parcel(s) or subclass(es) of Parcel or None
        if generic_check_issubclass(param.annotation, Parcel):
            checker: ModelField | None = None
            if param.annotation is not Parcel:
                checker = ModelField.construct(name=param.name, annotation=param.annotation, field_info=FieldInfo())
            return cls(checker=checker)
        # legacy: param is named "parcel" and has no type annotation
        elif param.annotation == param.empty and param.name == cls.KEYWORD:
            return cls()

    @override
    async def _solve(self, parcel: Parcel, **kwargs: Any) -> Any:
        return parcel

    @override
    async def _check(self, parcel: Parcel, **kwargs: Any) -> None:
        if self.checker is not None:
            check_field_type(self.checker, parcel)


def make_parcel_member_param(
    member: str, _check_param: Callable[[type[Param], inspect.Parameter, tuple[type["Param"], ...]], Any]
) -> type[Param]:
    if member not in Parcel.__dataclass_fields__:
        raise KeyError(f"{member} is not a dataclass field for Parcel")

    param_name = f"{member.title()}Param"

    def _init_(self: type, *args, checker: ModelField | None = None, **kwargs: Any) -> None:
        super(self.__class__, self).__init__(*args, **kwargs)
        self.checker = checker

    def _repr_(self) -> str:
        return f"{param_name}({repr(self.checker.annotation) if self.checker is not None else ''})"

    async def _solve(self, parcel: Parcel, **kwargs: Any) -> Any:
        return getattr(parcel, member)

    async def _check(self, parcel: Parcel, **kwargs: Any) -> None:
        if self.checker is not None:
            check_field_type(self.checker, getattr(parcel, member))

    return type(
        param_name,
        (Param,),
        {
            "__init__": _init_,
            "__repr__": _repr_,
            "_check_param": classmethod(_check_param),
            "_solve": _solve,
            "_check": _check,
        },
    )


def _check_payload_param(cls, param: inspect.Parameter, allow_types: tuple[type["Param"], ...]):
    checker: ModelField | None = None
    if param.name == "payload":
        if param.annotation != param.empty:
            checker = ModelField.construct(name=param.name, annotation=param.annotation, field_info=FieldInfo())

        return cls(checker=checker)


def _check_metadata_param(cls, param: inspect.Parameter, allow_types: tuple[type["Param"], ...]):
    if origin_is_annotated(get_origin(param.annotation)) and _METADATA_FLAG in get_args(param.annotation):
        return cls()
    elif param.name == "metadata":
        return cls()


def _check_receipt_parma(cls, param: inspect.Parameter, allow_types: tuple[type["Param"], ...]):
    if param.annotation is DeliveryReceipt:
        return cls()
    elif param.name == "receipt":
        return cls()


PayloadParam = make_parcel_member_param("payload", _check_payload_param)
"""`courier.Parcel.payload` 注入参数

本注入解析且仅解析名为 `payload` 的参数
"""

MetadataParam = make_parcel_member_param("metadata", _check_metadata_param)
"""`courier.Parcel.metadata` 注入参数

本注入解析：
- 名为 `metadata` 的参数
- 所有类型为且仅为`courier.Metadata`的参数
"""

ReceiptParam = make_parcel_member_param("receipt", _check_receipt_parma)
"""`courier.Parcel.receipt` 注入参数

本注入解析：
- 名为 `receipt` 的参数
- 所有类型为且仅为`courier.DeliveryReceipt`的参数
"""

if TYPE_CHECKING:
    PayloadParam = cast(type[Param], PayloadParam)
    MetadataParam = cast(type[Param], MetadataParam)
    ReceiptParam = cast(type[Param], ReceiptParam)

_MISSING = Sentinel("_MISSING")


@dataclass
class MetaKey:
    key: str | None
    default: Any | _MISSING


def MetaFetch(key: str | None = None, default: Any | _MISSING = _MISSING) -> Any:
    return MetaKey(key, default)


class MetaFetchParam(Param):
    """MetaFetch 注入参数

    本注入存储于 Parcel.metadata 的 key 所对应的 value。

    可以通过 `MetaFetch` 函数参数 `key` 指定获取的参数，
    留空则会根据参数名称获取。
    """

    def __init__(self, *args, key: str, default: Any | _MISSING, checker: ModelField | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.key = key
        self.fetch_default = default
        self.checker = checker

    def __repr__(self) -> str:
        return f"MetaFetchParam(key={self.key!r}, default={self.fetch_default!r}, checker={self.checker})"

    @classmethod
    @override
    def _check_param(cls, param: inspect.Parameter, allow_types: tuple[type["Param"], ...]) -> Self | None:
        # like a: list[str] = MetaFetch("b")
        checker: ModelField | None = None
        if isinstance(param.default, MetaKey):
            if param.annotation != param.empty:
                checker = ModelField.construct(name=param.name, annotation=param.annotation, field_info=FieldInfo())
            return cls(key=param.default.key or param.name, default=param.default.default, checker=checker)
        elif get_origin(param.annotation) is Annotated:
            checker = ModelField.construct(name=param.name, annotation=param.annotation, field_info=FieldInfo())
            for arg in get_args(param.annotation)[:0:-1]:
                if isinstance(arg, MetaKey):
                    return cls(key=arg.key or param.name, default=arg.default, checker=checker)

    @override
    async def _solve(self, parcel: Parcel, **kwargs: Any) -> Any:
        metadata = parcel.metadata
        if not metadata:
            if self.fetch_default is not _MISSING:
                return self.fetch_default
            raise KeyError(f"'{self.key}' not in {parcel.metadata=}")

        value = metadata.get(self.key, self.fetch_default)
        if value is _MISSING:
            raise KeyError(f"'{self.key}' not in {parcel.metadata=}")
        return value

    @override
    async def _check(self, parcel: Parcel, **kwargs: Any) -> None:
        if self.checker is not None:
            value = await self._solve(parcel=parcel)
            check_field_type(self.checker, value)


class DeadReasonParam(Param):
    """`courier.dead_letter_receiver` 的死信原因注入参数

    本注入解析类型为 `DEAD_REASON` 的参数。

    本注入还会解析名为 `dead_reason` 且没有类型注解的参数。
    """

    def __repr__(self) -> str:
        return "DeadReasonParam()"

    @classmethod
    @override
    def _check_param(cls, param: inspect.Parameter, allow_types: tuple[type[Param], ...]) -> Self | None:
        if origin_is_annotated(get_origin(param.annotation)) and _DEAD_REASON_FLAG in get_args(param.annotation):
            return cls()
        # legacy: param is named "state" and has no type annotation
        elif param.annotation == param.empty and param.name == "dead_reason":
            return cls()

    @override
    async def _solve(self, parcel: Parcel, **kwargs: Any) -> Any:
        return parcel.receipt.dead_reason


class ExceptionParam(Param):
    """`courier.dead_letter_receiver` 的异常注入参数

    本注入解析所有类型为 `Exception`、`ExceptionGroup` 或 `None` 的参数。

    本注入还会解析名为 `exception` 且没有类型注解的参数。
    """

    def __repr__(self) -> str:
        return "ExceptionParam()"

    @classmethod
    @override
    def _check_param(cls, param: inspect.Parameter, allow_types: tuple[type[Param], ...]) -> Self | None:
        # param type is Exception(s) or subclass(es) of Exception or None
        if generic_check_issubclass(param.annotation, (Exception, ExceptionGroup)):
            return cls()
        # legacy: param is named "exception" and has no type annotation
        elif param.annotation == param.empty and param.name == "exception":
            return cls()

    @override
    async def _solve(self, exception: Exception | ExceptionGroup[Exception] | None = None, **kwargs: Any) -> Any:
        return exception
