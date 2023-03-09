import importlib
import time
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


from ..config.subs_io import subscribes_export, subscribes_import

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


def import_yaml_module():
    try:
        pyyaml = importlib.import_module("yaml")
    except ImportError as e:
        raise ImportError("请使用 `pip install nonebot-bison[yaml]` 安装所需依赖") from e

    return pyyaml


@click.group()
def cli():
    """Nonebot Bison CLI"""
    pass


@cli.command(help="导出Nonebot Bison Exchangable Subcribes File", name="export")
@click.option("--path", "-p", default=None, help="导出路径")
@click.option("--yaml", is_flag=True, help="使用yaml格式")
@run_async
async def subs_export(path: Optional[str], yaml: bool):
    if yaml:
        logger.info("正在导出为yaml...")
        pyyaml = import_yaml_module()

        export_path = Path(path) if path else Path.cwd() / "data"
        try:
            assert export_path.exists()
        except AssertionError:
            export_path.mkdir()
        finally:
            export_file = (
                export_path / f"bison_subscribes_export_{int(time.time())}.yaml"
            )

            nbesf_data = await subscribes_export.build(echo=True)

            with export_file.open("w", encoding="utf-8") as f:
                pyyaml.safe_dump(nbesf_data, f, sort_keys=False)

        logger.success(f"导出完毕！已导出到{str(export_path)}")
    else:
        logger.info("正在导出json...")
        await subscribes_export.build()
        if path:
            logger.info(f"检测到指定导出路径: {path}")
            export_path = Path(path)
            await subscribes_export.export_to(export_path=export_path)
        else:
            logger.info("未指定导出路径，默认导出到{}".format(str(Path.cwd() / "data")))
            await subscribes_export.export_to()
            logger.success("导出完毕！")


@cli.command(help="从Nonebot Biosn Exchangable Subscribes File导入订阅", name="import")
@click.option("--path", "-p", required=True, help="导入文件名")
@click.option("--yaml", is_flag=True, help="从yaml文件读入")
@run_async
async def subs_import(path: str, yaml: bool):
    import_file_path = Path(path)
    assert import_file_path.is_file(), "该路径不是文件！"

    if yaml:
        logger.info("正在从yaml导入...")
        pyyaml = import_yaml_module()
        with import_file_path.open("r", encoding="utf-8") as f:
            import_items = pyyaml.safe_load(f)

            subscribes_import.load_from(import_items=import_items)
            await subscribes_import.dump_in()
    else:
        logger.info("正在从json导入...")
        subscribes_import.import_from(import_file_path=import_file_path)
        await subscribes_import.dump_in()


def main():
    anyio.run(run_sync(cli))  # pragma: no cover
