import json
from pathlib import Path
from unittest.mock import patch

from nonebug.app import App

from .utils import get_file, get_json


async def test_subs_export(app: App, init_scheduler, tmp_path: Path):
    import time

    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.subs_io import subscribes_export
    from nonebot_bison.types import Target as TTarget

    await config.add_subscribe(
        user=123,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=[],
    )
    await config.add_subscribe(
        user=234,
        user_type="group",
        target=TTarget("weibo_id"),
        target_name="weibo_name",
        platform_name="weibo",
        cats=[],
        tags=["kaltsit", "amiya"],
    )
    await config.add_subscribe(
        user=234,
        user_type="group",
        target=TTarget("bilibili_id"),
        target_name="bilibili_name",
        platform_name="bilibili",
        cats=[1, 2],
        tags=[],
    )

    data = await config.list_subs_with_all_info()
    assert len(data) == 3

    with patch("time.time") as mock_time:
        mock_now = mock_time.now.return_value
        mock_now.time.return_value = 1

        export_file = (
            tmp_path / "data" / f"bison_subscribes_export_{int(time.time())}.json"
        )

        assert not export_file.exists()
        await subscribes_export.build()
        await subscribes_export.export_to(tmp_path / "data")

        assert export_file.exists()
        with export_file.open() as f:
            export_json = json.load(f)

        assert export_json == get_json("subs_export.json")


async def test_subs_import(app: App, init_scheduler, tmp_path):
    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.subs_io import subscribes_import

    mock_file: Path = tmp_path / "1.json"
    mock_file.write_text(get_file("subs_export.json"))

    subscribes_import.import_from(mock_file)
    await subscribes_import.dump_in()

    data = await config.list_subs_with_all_info()

    assert len(data) == 3


async def test_subs_import_partical_err(app: App, init_scheduler, tmp_path):

    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.subs_io import subscribes_import

    mock_file: Path = tmp_path / "2.json"
    mock_file.write_text(get_file("subs_export_has_subdup_err.json"))

    subscribes_import.import_from(mock_file)
    await subscribes_import.dump_in()

    data = await config.list_subs_with_all_info()

    assert len(data) == 4


async def test_subs_import_all_fail(app: App, init_scheduler, tmp_path):
    """只要文件格式有任何一个错误， 都不会进行订阅"""
    from nonebot_bison.config.db_config import config
    from nonebot_bison.config.subs_io import subscribes_import

    mock_file: Path = tmp_path / "3.json"
    mock_file.write_text(get_file("subs_export_all_illegal.json"))

    subscribes_import.import_from(mock_file)
    await subscribes_import.dump_in()

    data = await config.list_subs_with_all_info()

    assert len(data) == 0
