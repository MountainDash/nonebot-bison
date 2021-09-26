from ..platform import platform_manager, check_sub_target
from .token_manager import token_manager
from .jwt import pack_jwt
from ..config import Config
import nonebot
from nonebot.adapters.cqhttp.bot import Bot

async def test():
    return {"status": 200, "text": "test"}

async def get_global_conf():
    res = {}
    for platform_name, platform in platform_manager.items():
        res[platform_name] = {
            'platformName': platform_name,
            'categories': platform.categories,
            'enabledTag': platform.enable_tag,
            'name': platform.name,
            'hasTarget': getattr(platform, 'has_target')
            }
    return { 'platformConf': res }


async def auth(token: str):
    if qq_tuple := token_manager.get_user(token):
        qq, nickname = qq_tuple
        bot = nonebot.get_bot()
        assert(isinstance(bot, Bot))
        groups = await bot.call_api('get_group_list')
        if str(qq) in nonebot.get_driver().config.superusers:
            jwt_obj = {
                    'id': str(qq),
                    'groups': list(map(
                        lambda info: {'id': info['group_id'], 'name': info['group_name']}, 
                        groups)),
                    }
            ret_obj = {
                    'type': 'admin',
                    'name': nickname,
                    'id': str(qq),
                    'token': pack_jwt(jwt_obj)
                    }
            return { 'status': 200, **ret_obj }
        else:
            return { 'status': 400, 'type': '', 'name': '', 'id': '', 'token': '' }
    else:
        return { 'status': 400, 'type': '', 'name': '', 'id': '', 'token': '' }

async def get_subs_info(jwt_obj: dict):
    groups = jwt_obj['groups']
    res = {}
    for group in groups:
        group_id = group['id']
        config = Config()
        subs = list(map(lambda sub: {
            'targetType': sub['target_type'], 'target': sub['target'], 'targetName': sub['target_name'], 'cats': sub['cats'], 'tags': sub['tags']
            }, config.list_subscribe(group_id, 'group')))
        res[group_id] = {
            'name': group['name'],
            'subscribes': subs
        }
    return res

async def get_target_name(platform_name: str, target: str, jwt_obj: dict):
    return {'targetName': await check_sub_target(platform_name, target)}
