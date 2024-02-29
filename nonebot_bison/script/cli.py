import json
import time
import importlib
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar
from functools import wraps, partial
from collections.abc import Callable, Coroutine

from nonebot.log import logger
from nonebot.compat import model_dump

from ..scheduler.manager import init_scheduler
from ..config.subs_io.nbesf_model import v1, v2
from ..config.subs_io import subscribes_export, subscribes_import

try:
    from typing_extensions import ParamSpec

    import anyio
    import click
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


def path_init(ctx, param, value):
    if not value:
        export_path = Path.cwd()
    else:
        export_path = Path(value)

    return export_path


@cli.command(help="导出Nonebot Bison Exchangable Subcribes File", name="export")
@click.option("--path", "-p", default=None, callback=path_init, help="导出路径,  如果不指定，则默认为工作目录")
@click.option(
    "--format",
    default="json",
    type=click.Choice(["json", "yaml", "yml"]),
    help="指定导出格式[json, yaml]，默认为 json",
)
@run_async
async def subs_export(path: Path, format: str):
    await init_scheduler()

    export_file = path / f"bison_subscribes_export_{int(time.time())}.{format}"

    logger.info("正在获取订阅信息...")
    export_data: v2.SubGroup = await subscribes_export(lambda x: x)

    with export_file.open("w", encoding="utf-8") as f:
        match format:
            case "yaml" | "yml":
                logger.info("正在导出为yaml...")

                pyyaml = import_yaml_module()
                # 由于 nbesf v2 中的user_target使用了AllSupportedPlatformTarget, 因此不能使用safe_dump
                # 下文引自 https://pyyaml.org/wiki/PyYAMLDocumentation
                # safe_dump(data, stream=None) serializes the given Python object into the stream.
                # If stream is None, it returns the produced stream.
                # safe_dump produces only standard YAML tags and cannot represent an arbitrary Python object.
                # 进行以下曲线救国方案
                json_data = json.dumps(model_dump(export_data), ensure_ascii=False)
                yaml_data = pyyaml.safe_load(json_data)
                pyyaml.safe_dump(yaml_data, f, sort_keys=False)

            case "json":
                logger.info("正在导出为json...")

                json.dump(model_dump(export_data), f, indent=4, ensure_ascii=False)

            case _:
                raise click.BadParameter(message=f"不支持的导出格式: {format}")

        logger.success(f"导出完毕！已导出到 {path} ")


@cli.command(help="从Nonebot Biosn Exchangable Subscribes File导入订阅", name="import")
@click.option("--path", "-p", required=True, help="导入文件名")
@click.option(
    "--format",
    default="json",
    type=click.Choice(["json", "yaml", "yml"]),
    help="指定导入格式[json, yaml]，默认为 json",
)
@run_async
async def subs_import(path: str, format: str):
    await init_scheduler()

    import_file_path = Path(path)
    assert import_file_path.is_file(), "该路径不是文件！"

    with import_file_path.open("r", encoding="utf-8") as f:
        match format:
            case "yaml" | "yml":
                logger.info("正在从yaml导入...")

                pyyaml = import_yaml_module()
                import_items = pyyaml.safe_load(f)

            case "json":
                logger.info("正在从json导入...")

                import_items = json.load(f)

            case _:
                raise click.BadParameter(message=f"不支持的导入格式: {format}")

        assert isinstance(import_items, dict)
        ver = int(import_items.get("version", 0))
        logger.info(f"NBESF版本: {ver}")
        match ver:
            case 1:
                nbesf_data = v1.nbesf_parser(import_items)
            case 2:
                nbesf_data = v2.nbesf_parser(import_items)
            case _:
                raise NotImplementedError("不支持的NBESF版本")

        await subscribes_import(nbesf_data)


def main():
    anyio.run(run_sync(cli))  # pragma: no cover
