from dataclasses import dataclass

from httpx import URL


@dataclass(eq=True, frozen=True)
class PlatformTarget:
    target: str
    platform_name: str
    target_name: str


class ApiError(Exception):
    def __init__(self, url: URL) -> None:
        msg = f"api {url} error"
        super().__init__(msg)
