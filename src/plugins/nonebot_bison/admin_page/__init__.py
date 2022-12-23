import os
from pathlib import Path
from typing import Union

import socketio
from fastapi.applications import FastAPI
from fastapi.staticfiles import StaticFiles
from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.drivers.fastapi import Driver
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..plugin_config import plugin_config
from .api import router as api_router
from .token_manager import token_manager as tm

STATIC_PATH = (Path(__file__).parent / "dist").resolve()

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, socketio_path="socket")


class SinglePageApplication(StaticFiles):
    def __init__(self, directory: os.PathLike, index="index.html"):
        self.index = index
        super().__init__(directory=directory, packages=None, html=True, check_dir=True)

    def lookup_path(self, path: str) -> tuple[str, Union[os.stat_result, None]]:
        full_path, stat_res = super().lookup_path(path)
        if stat_res is None:
            return super().lookup_path(self.index)
        return (full_path, stat_res)


def register_router_fastapi(driver: Driver, socketio):
    static_path = STATIC_PATH
    nonebot_app = FastAPI(
        title="nonebot-bison",
        description="nonebot-bison webui and api",
    )
    nonebot_app.include_router(api_router)
    nonebot_app.mount(
        "/", SinglePageApplication(directory=static_path), name="bison-frontend"
    )

    app = driver.server_app
    app.mount("/bison", nonebot_app, "nonebot-bison")


def init():
    driver = get_driver()
    if isinstance(driver, Driver):
        register_router_fastapi(driver, socket_app)
    else:
        logger.warning(f"Driver {driver.type} not supported")
        return
    host = str(driver.config.host)
    port = driver.config.port
    if host in ["0.0.0.0", "127.0.0.1"]:
        host = "localhost"
    logger.opt(colors=True).info(
        f"Nonebot test frontend will be running at: "
        f"<b><u>http://{host}:{port}/bison</u></b>"
    )


if (STATIC_PATH / "index.html").exists():
    init()

    get_token = on_command("后台管理", rule=to_me(), priority=5)

    @get_token.handle()
    async def send_token(bot: "Bot", event: PrivateMessageEvent, state: T_State):
        token = tm.get_user_token((event.get_user_id(), event.sender.nickname))
        await get_token.finish(f"请访问: {plugin_config.bison_outer_url}auth/{token}")

    get_token.__help__name__ = "获取后台管理地址"
    get_token.__help__info__ = "获取管理bot后台的地址，该地址会" "在一段时间过后过期，请不要泄漏该地址"
else:
    logger.warning(
        "Frontend file not found, please compile it or use docker or pypi version"
    )
