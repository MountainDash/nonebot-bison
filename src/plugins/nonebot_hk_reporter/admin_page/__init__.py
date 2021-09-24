import importlib
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from nonebot import get_driver, on_command
import nonebot
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.drivers.fastapi import Driver
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.typing import T_State
import socketio

from .api import test, get_global_conf, auth
from .token_manager import token_manager as tm
from ..plugin_config import plugin_config

URL_BASE = '/hk_reporter/'
GLOBAL_CONF_URL = f'{URL_BASE}api/global_conf'
AUTH_URL = f'{URL_BASE}api/auth'
TEST_URL = f'{URL_BASE}test'

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, socketio_path="socket")

def register_router_fastapi(driver: Driver, socketio):
    app = driver.server_app
    static_path = str((Path(__file__).parent / "dist").resolve())
    app.get(TEST_URL)(test)
    app.get(GLOBAL_CONF_URL)(get_global_conf)
    app.get(AUTH_URL)(auth)
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

get_token = on_command('后台管理', rule=to_me(), priority=5)
@get_token.handle()
async def send_token(bot: "Bot", event: PrivateMessageEvent, state: T_State):
    driver = nonebot.get_driver()
    superusers = driver.config.superusers
    if event.get_user_id() not in superusers:
        await get_token.finish('你不是管理员')
    else:
        token = tm.get_user_token((event.get_user_id(), event.sender.nickname))
        await get_token.finish(f'请访问: {plugin_config.hk_reporter_outer_url}auth/{token}')

