import importlib
import json
import time
from functools import partial, wraps
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Coroutine, Optional, TypeVar

from nonebot.log import logger

from nonebot_bison.config.db_config import config
from nonebot_bison.config.subs_io import (
    nbesf_parser,
    subscribes_export,
    subscribes_import,
)
from nonebot_bison.config.subs_io.nbesf_model import SubGroup
from nonebot_bison.scheduler.manager import init_scheduler

try:
    import anyio
    import click
    from typing_extensions import ParamSpec
except ImportError as e:  # pragma: no cover
    raise ImportError("请使用 `pip install nonebot-bison[cli]` 安装所需依赖") from e


def import_yaml_module() -> ModuleType:
    try:
        pyyaml = importlib.import_module("yaml")
    except ImportError as e:
        raise ImportError("请使用 `pip install nonebot-bison[yaml]` 安装所需依赖") from e

    return pyyaml


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


@cli.command(help="导出Nonebot Bison Exchangable Subcribes File", name="export")
@click.option("--path", "-p", default=None, help="导出路径")
@click.option("--yaml", is_flag=True, help="使用yaml格式")
@run_async
async def subs_export(path: Optional[str], yaml: bool):

    await init_scheduler()

    export_path = Path(path) if path else (Path.cwd() / "data")
    export_path.mkdir(exist_ok=True)
    export_file = (
        export_path
        / f"bison_subscribes_export_{int(time.time())}.{'yaml' if yaml else 'json'}"
    )

    logger.info("正在获取订阅信息...")
    export_data: SubGroup = await subscribes_export(config.list_subs_with_all_info)

    with export_file.open("w", encoding="utf-8") as f:
        if yaml:
            logger.info("正在导出为yaml...")

            pyyaml = import_yaml_module()
            pyyaml.safe_dump(export_data.dict(), f, sort_keys=False)
        else:
            logger.info("正在导出为json...")

            json.dump(export_data.dict(), f, indent=4, ensure_ascii=False)

        logger.success(f"导出完毕！已导出到 {str(export_path)} ")


@cli.command(help="从Nonebot Biosn Exchangable Subscribes File导入订阅", name="import")
@click.option("--path", "-p", required=True, help="导入文件名")
@click.option("--yaml", is_flag=True, help="从yaml文件读入")
@run_async
async def subs_import(path: str, yaml: bool):

    await init_scheduler()

    import_file_path = Path(path)
    assert import_file_path.is_file(), "该路径不是文件！"

    with import_file_path.open("r", encoding="utf-8") as f:
        if yaml:
            logger.info("正在从yaml导入...")

            pyyaml = import_yaml_module()
            import_items = pyyaml.safe_load(f)

        else:
            logger.info("正在从json导入...")

            import_items = json.load(f)

        nbesf_data = nbesf_parser(import_items)
        await subscribes_import(nbesf_data, config.add_subscribe)


def main():
    anyio.run(run_sync(cli))  # pragma: no cover
