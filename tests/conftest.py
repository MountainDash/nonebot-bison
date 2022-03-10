import asyncio
import typing
from pathlib import Path

import nonebot
import pytest
from nonebug.app import App


@pytest.fixture
async def app(nonebug_init: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import nonebot

    config = nonebot.get_driver().config
    config.bison_config_path = str(tmp_path)
    config.command_start = {""}
    config.superusers = {"10001"}
    config.log_level = "TRACE"
    config.bison_filter_log = False
    return App(monkeypatch)


@pytest.fixture
def dummy_user_subinfo(app: App):
    from nonebot_bison.types import User, UserSubInfo

    user = User(123, "group")
    return UserSubInfo(user=user, category_getter=lambda _: [], tag_getter=lambda _: [])


@pytest.fixture
def task_watchdog(request):
    def cancel_test_on_exception(task: asyncio.Task):
        def maybe_cancel_clbk(t: asyncio.Task):
            exception = t.exception()
            if exception is None:
                return

            for task in asyncio.all_tasks():
                coro = task.get_coro()
                if coro.__qualname__ == request.function.__qualname__:
                    task.cancel()
                    return

        task.add_done_callback(maybe_cancel_clbk)

    return cancel_test_on_exception
