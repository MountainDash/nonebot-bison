import importlib
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from nonebot import get_driver
from nonebot.drivers.fastapi import Driver
from nonebot.log import logger
import socketio

from .api import test, get_global_conf

URL_BASE = '/hk_reporter/'
GLOBAL_CONF_URL = f'{URL_BASE}api/global_conf'
TEST_URL = f'{URL_BASE}test'

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, socketio_path="socket")

def register_router_fastapi(driver: Driver, socketio):
    app = driver.server_app
    static_path = str((Path(__file__).parent / "dist").resolve())
    app.get(TEST_URL)(test)
    app.get(GLOBAL_CONF_URL)(get_global_conf)
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
                                 f"<b><u>http://{host}:{port}{URL_BASE}</u></b>")

init()
