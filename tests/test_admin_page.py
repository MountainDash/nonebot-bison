from pathlib import Path
from unittest.mock import patch

import pytest
from nonebug import App

from .utils import fake_admin_user, fake_private_message_event


@pytest.mark.asyncio
async def test_command(app: App):
    from nonebot.adapters.onebot.v11.bot import Bot
    from nonebot.adapters.onebot.v11.message import Message

    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.admin_page import register_get_token_handler
    from nonebot_bison.admin_page.token_manager import token_manager as tm

    with patch.object(tm, "get_user_token", return_value="test_token"):
        register_get_token_handler()

        async with app.test_matcher() as ctx:
            bot = ctx.create_bot(base=Bot)

            event_1 = fake_private_message_event(
                message=Message("后台管理"),
                sender=fake_admin_user,
                to_me=True,
            )
            ctx.receive_event(bot, event_1)
            ctx.should_call_send(event_1, f"请访问: {plugin_config.bison_outer_url}auth/test_token", True)
            ctx.should_finished()

            event_2 = fake_private_message_event(message=Message("管理后台"), sender=fake_admin_user, to_me=True)
            ctx.receive_event(bot, event_2)
            ctx.should_call_send(event_2, f"请访问: {plugin_config.bison_outer_url}auth/test_token", True)
            ctx.should_finished()


@pytest.mark.asyncio
async def test_log(app: App, tmp_path: Path):
    import io
    import contextlib

    from nonebot.log import logger, default_format

    from nonebot_bison.admin_page import init_fastapi

    log_path = tmp_path / "temp.log"

    logger.add(log_path, level="INFO", format=default_format, rotation="1 day")
    with contextlib.redirect_stderr(io.StringIO()) as f:
        init_fastapi()

    with log_path.open("r", encoding="utf-8") as f:
        log = f.read()
        assert "Nonebot Bison Migang frontend will be running at" in log
        assert "该页面不能被直接访问，请私聊bot 后台管理 以获取可访问地址" in log
