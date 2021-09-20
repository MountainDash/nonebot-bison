import importlib
import socketio
from nonebot import get_driver
from nonebot.log import logger
from nonebot.drivers.fastapi import Driver
from pathlib import Path
from fastapi.staticfiles import StaticFiles

URL_BASE = '/hk_reporter/'
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, socketio_path="socket")

def register_router_fastapi(driver: Driver, socketio):
    app = driver.server_app
    static_path = str((Path(__file__).parent / "dist").resolve())
    app.mount(URL_BASE, StaticFiles(directory=static_path, html=True), name="hk_reporter")

def init():
    driver = get_driver()
    if driver.type == 'fastapi':
        assert(isinstance(driver, Driver))
        register_router_fastapi(driver, socket_app)
    else:
        logger.warning(f"Driver {driver.type} not supported")
        return
    host = str(driver.config.host)
    port = driver.config.port
    if host in ["0.0.0.0", "127.0.0.1"]:
        host = "localhost"
    logger.opt(colors=True).info(f"Nonebot test frontend will be running at: "
                                 f"<b><u>http://{host}:{port}/test/</u></b>")

init()
