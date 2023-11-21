import nonebot
from fastapi import status
from fastapi.routing import APIRouter
from fastapi.param_functions import Depends
from fastapi.exceptions import HTTPException
from nonebot_plugin_saa import TargetQQGroup
from nonebot_plugin_saa.auto_select_bot import get_bot
from fastapi.security.oauth2 import OAuth2PasswordBearer

from ..types import WeightConfig
from ..apis import check_sub_target
from .jwt import load_jwt, pack_jwt
from ..types import Target as T_Target
from ..utils.get_bot import get_groups
from ..platform import platform_manager
from .token_manager import token_manager
from ..config.db_config import SubscribeDupException
from ..config import NoSuchUserException, NoSuchTargetException, NoSuchSubscribeException, config
from .types import (
    TokenResp,
    GlobalConf,
    StatusResp,
    SubscribeResp,
    PlatformConfig,
    AddSubscribeReq,
    SubscribeConfig,
    SubscribeGroupDetail,
)

router = APIRouter(prefix="/api", tags=["api"])

oath_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_jwt_obj(token: str = Depends(oath_scheme)):
    obj = load_jwt(token)
    if not obj:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return obj


async def check_group_permission(groupNumber: int, token_obj: dict = Depends(get_jwt_obj)):
    groups = token_obj["groups"]
    for group in groups:
        if int(groupNumber) == group["id"]:
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


async def check_is_superuser(token_obj: dict = Depends(get_jwt_obj)):
    if token_obj.get("type") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


@router.get("/global_conf")
async def get_global_conf() -> GlobalConf:
    res = {}
    for platform_name, platform in platform_manager.items():
        res[platform_name] = PlatformConfig(
            platformName=platform_name,
            categories=platform.categories,
            enabledTag=platform.enable_tag,
            name=platform.name,
            hasTarget=getattr(platform, "has_target"),
        )
    return GlobalConf(platformConf=res)


async def get_admin_groups(qq: int):
    res = []
    for group in await get_groups():
        group_id = group["group_id"]
        bot = get_bot(TargetQQGroup(group_id=group_id))
        if not bot:
            continue
        users = await bot.get_group_member_list(group_id=group_id)
        for user in users:
            if user["user_id"] == qq and user["role"] in ("owner", "admin"):
                res.append({"id": group_id, "name": group["group_name"]})
    return res


@router.get("/auth")
async def auth(token: str) -> TokenResp:
    if qq_tuple := token_manager.get_user(token):
        qq, nickname = qq_tuple
        if str(qq) in nonebot.get_driver().config.superusers:
            jwt_obj = {
                "id": qq,
                "type": "admin",
                "groups": [
                    {
                        "id": info["group_id"],
                        "name": info["group_name"],
                    }
                    for info in await get_groups()
                ],
            }
            ret_obj = TokenResp(
                type="admin",
                name=nickname,
                id=qq,
                token=pack_jwt(jwt_obj),
            )
            return ret_obj
        if admin_groups := await get_admin_groups(int(qq)):
            jwt_obj = {"id": str(qq), "type": "user", "groups": admin_groups}
            ret_obj = TokenResp(
                type="user",
                name=nickname,
                id=qq,
                token=pack_jwt(jwt_obj),
            )
            return ret_obj
        else:
            raise HTTPException(400, "permission denied")
    else:
        raise HTTPException(400, "code error")


@router.get("/subs")
async def get_subs_info(jwt_obj: dict = Depends(get_jwt_obj)) -> SubscribeResp:
    groups = jwt_obj["groups"]
    res: SubscribeResp = {}
    for group in groups:
        group_id = group["id"]
        raw_subs = await config.list_subscribe(TargetQQGroup(group_id=group_id))
        subs = [
            SubscribeConfig(
                platformName=sub.target.platform_name,
                targetName=sub.target.target_name,
                cats=sub.categories,
                tags=sub.tags,
                target=sub.target.target,
            )
            for sub in raw_subs
        ]
        res[group_id] = SubscribeGroupDetail(name=group["name"], subscribes=subs)
    return res


@router.get("/target_name", dependencies=[Depends(get_jwt_obj)])
async def get_target_name(platformName: str, target: str):
    return {"targetName": await check_sub_target(platformName, T_Target(target))}


@router.post("/subs", dependencies=[Depends(check_group_permission)])
async def add_group_sub(groupNumber: int, req: AddSubscribeReq) -> StatusResp:
    try:
        await config.add_subscribe(
            TargetQQGroup(group_id=groupNumber),
            T_Target(req.target),
            req.targetName,
            req.platformName,
            req.cats,
            req.tags,
        )
        return StatusResp(ok=True, msg="")
    except SubscribeDupException:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "subscribe duplicated")


@router.delete("/subs", dependencies=[Depends(check_group_permission)])
async def del_group_sub(groupNumber: int, platformName: str, target: str):
    try:
        await config.del_subscribe(TargetQQGroup(group_id=groupNumber), target, platformName)
    except (NoSuchUserException, NoSuchSubscribeException):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no such user or subscribe")
    return StatusResp(ok=True, msg="")


@router.patch("/subs", dependencies=[Depends(check_group_permission)])
async def update_group_sub(groupNumber: int, req: AddSubscribeReq):
    try:
        await config.update_subscribe(
            TargetQQGroup(group_id=groupNumber),
            req.target,
            req.targetName,
            req.platformName,
            req.cats,
            req.tags,
        )
    except (NoSuchUserException, NoSuchSubscribeException):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no such user or subscribe")
    return StatusResp(ok=True, msg="")


@router.get("/weight", dependencies=[Depends(check_is_superuser)])
async def get_weight_config():
    return await config.get_all_weight_config()


@router.put("/weight", dependencies=[Depends(check_is_superuser)])
async def update_weigth_config(platformName: str, target: str, weight_config: WeightConfig):
    try:
        await config.update_time_weight_config(T_Target(target), platformName, weight_config)
    except NoSuchTargetException:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no such subscribe")
    return StatusResp(ok=True, msg="")
