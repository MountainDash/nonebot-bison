import json
from unittest.mock import mock_open, patch

from nonebug.app import App


async def test_export(app: App, init_scheduler):
    import time
    from pathlib import Path

    from nonebot_bison.config.db import subscribes_dump, subscribes_export
    from nonebot_bison.config.db_config import config
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

    static_path = Path(__file__).parent / "static"

    with open(static_path / "subs_export.json", "r", encoding="utf-8") as f:
        expected_json = json.load(f)

    export_json = await subscribes_export()
    assert export_json == expected_json

    with patch("time.time") as mock_time:
        mock_now = mock_time.now.return_value
        mock_now.time.return_value = 1

        with patch("builtins.open", mock_open()) as mock_file:
            await subscribes_dump(export_json)

            mock_file.assert_called_once_with(
                Path.cwd()
                / "data"
                / f"bison_subscribes_export_{int(time.time())}.json",
                "w",
                encoding="utf-8",
            )
