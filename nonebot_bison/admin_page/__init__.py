import os
from pathlib import Path
from typing import TYPE_CHECKING

from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import PrivateMessageEvent

from .api import router as api_router
from ..plugin_config import plugin_config
from .token_manager import token_manager as tm

if TYPE_CHECKING:
    from nonebot.drivers.fastapi import Driver


STATIC_PATH = (Path(__file__).parent / "dist").resolve()


def init_fastapi(driver: "Driver"):
    import socketio
    from fastapi.applications import FastAPI
    from fastapi.staticfiles import StaticFiles

    sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
    socket_app = socketio.ASGIApp(sio, socketio_path="socket")

    class SinglePageApplication(StaticFiles):
        def __init__(self, directory: os.PathLike, index="index.html"):
            self.index = index
            super().__init__(directory=directory, packages=None, html=True, check_dir=True)

        def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
            full_path, stat_res = super().lookup_path(path)
            if stat_res is None:
                return super().lookup_path(self.index)
            return (full_path, stat_res)

    def register_router_fastapi(driver: "Driver", socketio):
        static_path = STATIC_PATH
        nonebot_app = FastAPI(
            title="nonebot-bison",
            description="nonebot-bison webui and api",
        )
        nonebot_app.include_router(api_router)
        nonebot_app.mount("/", SinglePageApplication(directory=static_path), name="bison-frontend")

        app = driver.server_app
        app.mount("/bison", nonebot_app, "nonebot-bison")

    register_router_fastapi(driver, socket_app)
    host = str(driver.config.host)
    port = driver.config.port
    if host in ["0.0.0.0", "127.0.0.1"]:
        host = "localhost"
    logger.opt(colors=True).info(f"Nonebot Bison frontend will be running at: <b><u>http://{host}:{port}/bison</u></b>")
    logger.opt(colors=True).info("该页面不能被直接访问，请私聊bot <b><u>后台管理</u></b> 以获取可访问地址")


def register_get_token_handler():
    get_token = on_command("后台管理", rule=to_me(), priority=5, aliases={"管理后台"})

    @get_token.handle()
    async def send_token(bot: "Bot", event: PrivateMessageEvent, state: T_State):
        token = tm.get_user_token((event.get_user_id(), event.sender.nickname))
        await get_token.finish(f"请访问: {plugin_config.outer_url / 'auth' / token}")

    get_token.__help__name__ = "获取后台管理地址"  # type: ignore
    get_token.__help__info__ = "获取管理bot后台的地址，该地址会在一段时间过后过期，请不要泄漏该地址"  # type: ignore


def get_fastapi_driver() -> "Driver | None":
    try:
        from nonebot.drivers.fastapi import Driver

        if (driver := get_driver()) and isinstance(driver, Driver):
            return driver
        return None

    except ImportError:
        return None


if (STATIC_PATH / "index.html").exists():
    if driver := get_fastapi_driver():
        init_fastapi(driver)
        register_get_token_handler()
    else:
        logger.warning("your driver is not fastapi, webui feature will be disabled")
else:
    logger.warning("Frontend file not found, please compile it or use docker or pypi version")
