from collections.abc import Callable
from typing import Concatenate

type ClassPropertyGetFunc[V, **P, R] =Callable[Concatenate[type[V], P], R] | classmethod[V, [], R]

class ClassPropertyDescriptor[V, **P, R]:

    def __init__(self, fget: ClassPropertyGetFunc[V, P, R], fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, class_=None):
        if class_ is None:
            class_ = type(obj)
        return self.fget.__get__(obj, class_)()


def classproperty[V, **P, R](func: ClassPropertyGetFunc[V, P, R]):
    """将类方法转化为类属性

    e.g.
    ```python
    class Example:
        @classproperty
        @classmethod
        def name(cls) -> str:
            return cls.__name__

    print(Example.name)  # 输出 "Example"

    ```
    """

    return ClassPropertyDescriptor(func)
