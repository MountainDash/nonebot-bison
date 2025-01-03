from typing import cast

from fastapi import status
from fastapi.exceptions import HTTPException
from fastapi.param_functions import Depends
from fastapi.routing import APIRouter
from fastapi.security.oauth2 import OAuth2PasswordBearer
import nonebot
from nonebot_plugin_saa import TargetQQGroup
from nonebot_plugin_saa.auto_select_bot import get_bot

from nonebot_bison.apis import check_sub_target
from nonebot_bison.config import NoSuchSubscribeException, NoSuchTargetException, NoSuchUserException, config
from nonebot_bison.config.db_config import SubscribeDupException
from nonebot_bison.platform import platform_manager
from nonebot_bison.scheduler import scheduler_dict
from nonebot_bison.types import Target as T_Target
from nonebot_bison.types import WeightConfig
from nonebot_bison.utils.get_bot import get_groups
from nonebot_bison.utils.site import CookieClientManager, is_cookie_client_manager, site_manager

from .jwt import load_jwt, pack_jwt
from .token_manager import token_manager
from .types import (
    AddSubscribeReq,
    Cookie,
    CookieTarget,
    GlobalConf,
    PlatformConfig,
    SiteConfig,
    StatusResp,
    SubscribeConfig,
    SubscribeGroupDetail,
    SubscribeResp,
    Target,
    TokenResp,
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
    platform_res = {}
    for platform_name, platform in platform_manager.items():
        platform_res[platform_name] = PlatformConfig(
            platformName=platform_name,
            categories=platform.categories,
            enabledTag=platform.enable_tag,
            siteName=platform.site.name,
            name=platform.name,
            hasTarget=getattr(platform, "has_target"),
        )
    site_res = {}
    for site_name, site in site_manager.items():
        site_res[site_name] = SiteConfig(name=site_name, enable_cookie=is_cookie_client_manager(site.client_mgr))
    return GlobalConf(platformConf=platform_res, siteConf=site_res)


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


@router.get("/cookie", dependencies=[Depends(check_is_superuser)])
async def get_cookie(site_name: str | None = None, target: str | None = None) -> list[Cookie]:
    cookies_in_db = await config.get_cookie(site_name, is_anonymous=False)
    return [
        Cookie(
            id=cookies_in_db[i].id,
            content=cookies_in_db[i].content,
            cookie_name=cookies_in_db[i].cookie_name,
            site_name=cookies_in_db[i].site_name,
            last_usage=cookies_in_db[i].last_usage,
            status=cookies_in_db[i].status,
            cd_milliseconds=cookies_in_db[i].cd_milliseconds,
            is_universal=cookies_in_db[i].is_universal,
            is_anonymous=cookies_in_db[i].is_anonymous,
            tags=cookies_in_db[i].tags,
        )
        for i in range(len(cookies_in_db))
    ]


@router.post("/cookie", dependencies=[Depends(check_is_superuser)])
async def add_cookie(site_name: str, content: str) -> StatusResp:
    client_mgr = cast(CookieClientManager, scheduler_dict[site_manager[site_name]].client_mgr)
    await client_mgr.add_identified_cookie(content)
    return StatusResp(ok=True, msg="")


@router.delete("/cookie/{cookie_id}", dependencies=[Depends(check_is_superuser)])
async def delete_cookie_by_id(cookie_id: int) -> StatusResp:
    await config.delete_cookie_by_id(cookie_id)
    return StatusResp(ok=True, msg="")


@router.get("/cookie_target", dependencies=[Depends(check_is_superuser)])
async def get_cookie_target(
    site_name: str | None = None, target: str | None = None, cookie_id: int | None = None
) -> list[CookieTarget]:
    cookie_targets = await config.get_cookie_target()
    # TODO: filter in SQL
    return [
        CookieTarget(
            target=Target(
                platform_name=x.target.platform_name, target_name=x.target.target_name, target=x.target.target
            ),
            cookie_id=x.cookie.id,
        )
        for x in cookie_targets
        if (site_name is None or x.cookie.site_name == site_name)
        and (target is None or x.target.target == target)
        and (cookie_id is None or x.cookie.id == cookie_id)
    ]


@router.post("/cookie_target", dependencies=[Depends(check_is_superuser)])
async def add_cookie_target(platform_name: str, target: T_Target, cookie_id: int) -> StatusResp:
    await config.add_cookie_target(target, platform_name, cookie_id)
    return StatusResp(ok=True, msg="")


@router.delete("/cookie_target", dependencies=[Depends(check_is_superuser)])
async def del_cookie_target(platform_name: str, target: T_Target, cookie_id: int) -> StatusResp:
    await config.delete_cookie_target(target, platform_name, cookie_id)
    return StatusResp(ok=True, msg="")


@router.post("/cookie/validate", dependencies=[Depends(check_is_superuser)])
async def get_cookie_valid(site_name: str, content: str) -> StatusResp:
    client_mgr = cast(CookieClientManager, scheduler_dict[site_manager[site_name]].client_mgr)
    if await client_mgr.validate_cookie(content):
        return StatusResp(ok=True, msg="")
    else:
        return StatusResp(ok=False, msg="")
