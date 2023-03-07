import json
from pathlib import Path
from unittest.mock import patch

import pytest
from nonebug.app import App


@pytest.fixture(scope="module")
def expected_json():
    static_path = Path(__file__).parent / "static"

    with open(static_path / "subs_export.json", "r", encoding="utf-8") as f:
        expected_json = json.load(f)

    return expected_json


async def test_export(app: App, init_scheduler, tmp_path: Path, expected_json):
    import time

    from nonebot_bison.config.db_config import config
    from nonebot_bison.subs_io import subscribes_export
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
        await subscribes_export(tmp_path / "data")

        assert export_file.exists()
        with export_file.open() as f:
            export_json = json.load(f)

        assert export_json == expected_json
