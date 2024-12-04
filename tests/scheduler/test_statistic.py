from textwrap import dedent
from datetime import datetime
from typing import TYPE_CHECKING
from collections import defaultdict
from unittest.mock import Mock, AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from nonebot_bison.scheduler.statistic import RuntimeStatistic


@pytest.fixture
def runtime_statistic():
    from nonebot_bison.scheduler.statistic import RuntimeStatistic

    return RuntimeStatistic()


@pytest.mark.asyncio
async def test_statistic_schedule_count(app, runtime_statistic: "RuntimeStatistic"):
    mock_func = AsyncMock()
    mock_func.return_value = AsyncMock(platform_name="test_platform", target="test_target")

    decorated_func = runtime_statistic.statistic_schedule_count(mock_func)
    await decorated_func()

    assert runtime_statistic._record["schedule_count"]["test_platform"]["test_target"] == 1


@pytest.mark.asyncio
async def test_statistic_schedule_count_no_schedulable(app, runtime_statistic: "RuntimeStatistic"):
    mock_func = AsyncMock()
    mock_func.return_value = None

    decorated_func = runtime_statistic.statistic_schedule_count(mock_func)
    await decorated_func()

    assert "test_platform" not in runtime_statistic._record["schedule_count"]


@pytest.mark.asyncio
async def test_statistic_record_insert_new(app, runtime_statistic: "RuntimeStatistic"):
    mock_func = AsyncMock()
    mock_self = Mock()

    decorated_func = runtime_statistic.statistic_record("insert_new")(mock_func)
    with patch("nonebot_bison.scheduler.statistic.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2023, 1, 1)
        await decorated_func(mock_self, "test_platform", "test_target")  # type: ignore

    assert runtime_statistic._record["insert_new"] == [("test_platform-test_target", datetime(2023, 1, 1))]


@pytest.mark.asyncio
async def test_statistic_record_delete(app, runtime_statistic: "RuntimeStatistic"):
    mock_func = AsyncMock()
    mock_self = Mock()

    decorated_func = runtime_statistic.statistic_record("delete")(mock_func)
    with patch("nonebot_bison.scheduler.statistic.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2023, 1, 2)
        await decorated_func(mock_self, "test_platform", "test_target")  # type: ignore

    assert runtime_statistic._record["delete"] == [("test_platform-test_target", datetime(2023, 1, 2))]


@pytest.mark.asyncio
async def test_statistic_record_report_generate(app, runtime_statistic: "RuntimeStatistic"):
    from nonebot_bison.utils import Site
    from nonebot_bison.scheduler.scheduler import Scheduler

    class MockSite(Site):
        name = "test_site"
        schedule_type = "interval"
        schedule_setting = {"seconds": 100}

    scheduler_dict: dict[type[Site], Scheduler] = {MockSite: Scheduler(MockSite, [], [])}
    _mock_record = defaultdict(int)
    _mock_record["test_target"] = 1
    runtime_statistic._record["schedule_count"]["test_platform"] = _mock_record
    runtime_statistic._record["insert_new"] = [("test_platform-test_target", datetime(2023, 1, 1))]
    runtime_statistic._record["delete"] = [("test_platform-test_target", datetime(2023, 1, 1))]

    report = runtime_statistic._generate_stats(scheduler_dict)

    assert report == {
        "新增订阅hook调用记录": [f"test_platform-test_target: {datetime(2023, 1, 1).strftime('%Y-%m-%d %H:%M:%S')}"],
        "删除订阅hook调用记录": [f"test_platform-test_target: {datetime(2023, 1, 1).strftime('%Y-%m-%d %H:%M:%S')}"],
        "调度统计": {"test_platform": ["test_target: 1 次"]},
        "所有调度对象": {"test_site": []},
        "发送消息统计": {},
    }

    repost_str = runtime_statistic.generate_report(scheduler_dict)
    assert (
        repost_str
        == dedent(
            """
        新增订阅hook调用记录:
          test_platform-test_target: 2023-01-01 00:00:00
        删除订阅hook调用记录:
          test_platform-test_target: 2023-01-01 00:00:00
        调度统计:
          test_platform:
            test_target: 1 次
        发送消息统计:
        所有调度对象:
          test_site:
        """
        )[1:]
    )  # 不要第一个换行符
