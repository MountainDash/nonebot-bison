import os
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import socketio
from fastapi.staticfiles import StaticFiles
from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.drivers.fastapi import Driver
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.typing import T_State

from ..plugin_config import plugin_config
from ..types import WeightConfig
from .api import (
    add_group_sub,
    auth,
    del_group_sub,
    get_global_conf,
    get_subs_info,
    get_target_name,
    get_weight_config,
    test,
    update_group_sub,
    update_weigth_config,
)
from .jwt import load_jwt
from .token_manager import token_manager as tm

URL_BASE = "/bison/"
GLOBAL_CONF_URL = f"{URL_BASE}api/global_conf"
AUTH_URL = f"{URL_BASE}api/auth"
SUBSCRIBE_URL = f"{URL_BASE}api/subs"
GET_TARGET_NAME_URL = f"{URL_BASE}api/target_name"
WEIGHT_URL = f"{URL_BASE}api/weight"
TEST_URL = f"{URL_BASE}test"

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
    from fastapi import HTTPException, status
    from fastapi.param_functions import Depends
    from fastapi.security import OAuth2PasswordBearer

    oath_scheme = OAuth2PasswordBearer(tokenUrl="token")

    async def get_jwt_obj(token: str = Depends(oath_scheme)):
        obj = load_jwt(token)
        if not obj:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return obj

    async def check_group_permission(
        groupNumber: int, token_obj: dict = Depends(get_jwt_obj)
    ):
        groups = token_obj["groups"]
        for group in groups:
            if int(groupNumber) == group["id"]:
                return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    async def check_is_superuser(token_obj: dict = Depends(get_jwt_obj)):
        if token_obj.get("type") != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    @dataclass
    class AddSubscribeReq:
        platformName: str
        target: str
        targetName: str
        cats: list[int]
        tags: list[str]

    app = driver.server_app
    static_path = STATIC_PATH
    app.get(TEST_URL)(test)
    app.get(GLOBAL_CONF_URL)(get_global_conf)
    app.get(AUTH_URL)(auth)

    @app.get(SUBSCRIBE_URL)
    async def subs(jwt_obj: dict = Depends(get_jwt_obj)):
        return await get_subs_info(jwt_obj)

    @app.get(GET_TARGET_NAME_URL)
    async def _get_target_name(
        platformName: str, target: str, jwt_obj: dict = Depends(get_jwt_obj)
    ):
        return await get_target_name(platformName, target, jwt_obj)

    @app.post(SUBSCRIBE_URL, dependencies=[Depends(check_group_permission)])
    async def _add_group_subs(groupNumber: int, req: AddSubscribeReq):
        return await add_group_sub(
            group_number=groupNumber,
            platform_name=req.platformName,
            target=req.target,
            target_name=req.targetName,
            cats=req.cats,
            tags=req.tags,
        )

    @app.patch(SUBSCRIBE_URL, dependencies=[Depends(check_group_permission)])
    async def _update_group_subs(groupNumber: int, req: AddSubscribeReq):
        return await update_group_sub(
            group_number=groupNumber,
            platform_name=req.platformName,
            target=req.target,
            target_name=req.targetName,
            cats=req.cats,
            tags=req.tags,
        )

    @app.delete(SUBSCRIBE_URL, dependencies=[Depends(check_group_permission)])
    async def _del_group_subs(groupNumber: int, target: str, platformName: str):
        return await del_group_sub(groupNumber, platformName, target)

    @app.get(WEIGHT_URL, dependencies=[Depends(check_is_superuser)])
    async def _get_weight_config():
        return await get_weight_config()

    @app.put(WEIGHT_URL, dependencies=[Depends(check_is_superuser)])
    async def _update_weight_config(platform_name: str, target: str, req: WeightConfig):
        return await update_weigth_config(platform_name, target, req)

    app.mount(URL_BASE, SinglePageApplication(directory=static_path), name="bison")


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
        f"<b><u>http://{host}:{port}{URL_BASE}</u></b>"
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
