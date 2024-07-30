from typing import Protocol, runtime_checkable


@runtime_checkable
class PlainContentSupport(Protocol):
    async def get_plain_content(self) -> str: ...


@runtime_checkable
class HTMLContentSupport(Protocol):
    async def get_html_content(self) -> str: ...


@runtime_checkable
class MarkdownContentSupport(Protocol):
    async def get_markdown_content(self) -> str: ...
