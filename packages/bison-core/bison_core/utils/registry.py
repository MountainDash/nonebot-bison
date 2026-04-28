from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, assert_never, overload

from nonebot import logger

if TYPE_CHECKING:
    from collections.abc import Callable

type RegistryType[T] = dict[str, type[T]]


class RegistryException(Exception):
    registry_name: str

    def __init__(self, registry_name: str, *args: Any) -> None:
        super().__init__(*args)
        self.registry_name = registry_name


class RegisteredClassCheckError(RegistryException):
    pass


class RegistryHookExistError(RegistryException):
    pass


class RegistryRemoveError(RegistryException):
    pass


class RegistryDuplicateError(RegistryException):
    pass


type CheckerType[T] = Callable[[type[T]], bool]
type RegisterHookType[T] = Callable[[type[T]], None]

@dataclass
class Registry[T]:
    name: str
    checker: CheckerType[T] | None = None
    register_hooker: RegisterHookType[T] | None = None

    def __post_init__(self) -> None:
        self._member: RegistryType[T] = {}

    @overload
    def register(self, name: type[T]) -> type[T]: ...

    @overload
    def register(
        self, /, name: str | None = None, raise_on_failure: bool = True, allow_overwrite: bool = False
    ) -> Callable[[type[T]], type[T]]: ...

    def register(
        self, name: type[T] | str | None = None, raise_on_failure: bool = True, allow_overwrite: bool = False
    ) -> type[T] | Callable[[type[T]], type[T]]:
        def register_func(cls: type[T], member_name: str | None = None) -> type[T]:
            check_res = True
            if c := self.checker:
                try:
                    check_res = c(cls)
                except Exception as e:
                    raise RegisteredClassCheckError(
                        self.name,
                        f"class {cls.__name__} can't pass Registry[{self.name}]'s checker with error",
                    ) from e
            match check_res, raise_on_failure:
                case True, _:
                    name = member_name or cls.__name__
                    if name in self._member:
                        if not allow_overwrite:
                            raise RegistryDuplicateError(
                                self.name, f"Member {name} already exists in Registry[{self.name}]"
                            )
                        else:
                            logger.opt(colors=True).warning(
                                f"Member <b><u>{name}</u></b> already exists in Registry[{self.name}], overwriting it"
                            )

                    self._member[name] = cls
                    if hook := self.register_hooker:
                        hook(cls)
                case False, True:
                    raise RegisteredClassCheckError(
                        self.name,
                        f"class {cls.__name__} can't pass Registry[{self.name}]'s checker",
                    )
                case _:
                    logger.info(f"class {cls.__name__} can't pass Registry[{self.name}]'s checker, ignoring...")

            return cls

        match name:
            case str() as n:
                return partial(register_func, member_name=n)
            case type() as t:
                return register_func(cls=t, member_name=None)
            case None:
                return register_func
            case _:
                assert_never(name)

    def unregister(self, name: str) -> None:
        if name not in self._member:
            raise RegistryRemoveError(self.name, f"Registry[{self.name}] has no member named {name}")

        del self._member[name]

    def members(self) -> dict[str, type[T]]:
        return self._member

    def as_checker(self, func: CheckerType[T]) -> CheckerType[T]:
        if self.checker is not None:
            raise RegistryHookExistError(self.name, f"Checker for Registry[{self.name}] already exists")

        self.checker = func
        return func

    def on_post_register(self, func: RegisterHookType[T]) -> RegisterHookType[T]:
        if self.register_hooker is not None:
            raise RegistryHookExistError(self.name, f"Post-register hook for Registry[{self.name}] already exists")

        self.register_hooker = func
        return func

    def __contains__(self, name: str) -> bool:
        return name in self._member

    def __len__(self) -> int:
        return len(self._member)

    def __getitem__(self, name: str) -> type[T]:
        return self._member[name]

    def get_member(self, name: str) -> type[T] | None:
        return self._member.get(name)

class Registries:
    _store: ClassVar[dict[str, Registry[Any]]] = {}

    @classmethod
    def as_registry[T](cls, name: str) -> Registry[T]:
        registry = Registry(name)
        cls._store[name] = registry
        return registry

    @classmethod
    def get_registry[T](cls, name: str) -> Registry[T]:
        if name not in cls._store:
            raise RegistryException(name, f"Registry[{name}] does not exist")
        return cls._store[name]
