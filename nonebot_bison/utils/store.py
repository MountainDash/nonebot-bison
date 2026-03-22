from typing import Any, override

from nonebot_bison.core.site import StoreLike


class MemoryStore(StoreLike):
    """In-memory storage implementation."""

    _inner: dict[str, Any]
    inited: bool = False

    @override
    def on_init(self) -> None:
        self._inner = {}
        self.inited = True

    @override
    def __getitem__(self, key: str, /) -> Any:
        self._inner[key]

    @override
    def __setitem__(self, key: str, value: Any, /) -> None:
        self._inner[key] = value

    @override
    def __contains__(self, key: str, /) -> bool:
        return key in self._inner
