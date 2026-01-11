from typing import Any, ClassVar
from typing_extensions import Sentinel

from nonebot_bison.utils.classproperty import classproperty

type RegisteredClass = Any
"""需要注册的类的基类"""

type _RegisteredName = str
type _BaseClassName = str

type Registry = dict[_RegisteredName, RegisteredClass]
type _Registries = dict[_BaseClassName, Registry]

_MISSING_ = Sentinel("_MISSING_")

class RegistryMeta(type):
    __base: str
    __registries: ClassVar[_Registries] = {}
    def __new__(cls, name, bases, namespace, **kwargs):
        return super().__new__(cls, name, bases, namespace)

    def __init__(cls, name, bases, namespace, **kwargs):
        is_abstract: bool = kwargs.get("abstract", False)
        match base := kwargs.get("base", _MISSING_):
            case str():
                cls.__registries[base] = {}
                # 先不考虑存在base之后再定义base的情况，没有实际需求，有需要再说
                cls.__base = base
                cls.name = classproperty(classmethod(lambda cls: base))
            case True:
                # 没有指定 base 的具体值，使用类名
                cls.__registries[name] = {}
                cls.__base = name
                cls.name = classproperty(classmethod(lambda cls: name))
            case other if other is _MISSING_ and not is_abstract:
                #this is a subclass
                match cls.name:
                    case None:
                        raise TypeError("Registered class must implement 'name' classproperty")
                    case class_name if class_name in cls.__registries.get(cls.__base, {}):
                        raise KeyError(f"Duplicate registered class name: {class_name}")
                    case class_name if isinstance(class_name, str):
                        cls.__registries[cls.__base][class_name] = cls
                    case _:
                        raise TypeError(f"Registered class name must be str, got {type(cls.name)}")

            case other if other is _MISSING_ and is_abstract:
                #abstract subclass
                pass
            case _:
                raise TypeError(f"Invalid registry meta class args: {base=}, {is_abstract=}")

        super().__init__(name, bases, namespace, **kwargs)

    @property
    def registry(cls) -> Registry:
        return cls.__registries.get(cls.__base, {})

    @property
    def base(cls) -> str:
        return cls.__base

    @classproperty
    @classmethod
    def name(cls) -> str:
        """注册类的名称"""
        raise NotImplementedError("Registered class must implement 'name' classproperty")
