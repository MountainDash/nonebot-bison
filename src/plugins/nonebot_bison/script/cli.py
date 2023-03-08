from functools import partial, wraps
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional, TypeVar

from nonebot.log import logger

try:
    import anyio
    import click
    from typing_extensions import ParamSpec
except ImportError as e:  # pragma: no cover
    raise ImportError("请使用 `pip install nonebot-bison[cli]` 安装所需依赖") from e


from ..subs_io import subscribes_export, subscribes_import

P = ParamSpec("P")
R = TypeVar("R")


def run_sync(func: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await anyio.to_thread.run_sync(partial(func, *args, **kwargs))

    return wrapper


def run_async(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return anyio.from_thread.run(partial(func, *args, **kwargs))

    return wrapper


@click.group()
def cli():
    """Nonebot Bison CLI"""
    pass


@cli.command(help="导出Nonebot Bison Exchangable Subcribes File")
@click.option("--path", "-p", default=None, help="导出路径")
@click.option("--yaml", is_flag=True, help="使用yaml格式")
@run_async
async def export(path: Optional[str], yaml: bool):
    export_path = Path(path)

    await subscribes_export(export_path=export_path)


@cli.command(help="从Nonebot Biosn Exchangable Subscribes File导入订阅")
@click.option("--path", "-p", help="导入文件名")
@click.option("--yaml", is_flag=True, help="从yaml文件读入")
@run_async
async def import_(path: str, yaml: bool):
    import_file_path = Path(path)

    await subscribes_import(import_file_path=import_file_path)


def main():
    anyio.run(run_sync(cli))  # pragma: no cover
