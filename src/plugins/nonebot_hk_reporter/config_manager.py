from nonebot import logger, on_command
from nonebot.adapters.cqhttp import Bot, Event, GroupMessageEvent
from nonebot.adapters.cqhttp.message import Message
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_MEMBER, GROUP_OWNER
from nonebot.permission import Permission, SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State

from .config import Config, NoSuchSubscribeException
from .platform import platform_manager
from .platform.utils import check_sub_target
from .send import send_msgs
from .utils import parse_text
from .types import Target

help_match = on_command('help', rule=to_me(), priority=5)
@help_match.handle()
async def send_help(bot: Bot, event: Event, state: T_State):
    message = '使用方法：\n@bot 添加订阅（仅管理员）\n@bot 查询订阅\n@bot 删除订阅（仅管理员）'
    await help_match.finish(Message(await parse_text(message)))

add_sub = on_command("添加订阅", rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER, priority=5)
@add_sub.got('platform', '请输入想要订阅的平台，目前支持：{}'.format(', '.join(platform_manager.keys())))
# @add_sub.got('id', '请输入订阅用户的id，详情查阅https://github.com/felinae98/nonebot-hk-reporter')
@add_sub.handle()
async def add_sub_handle_id(bot: Bot, event: Event, state: T_State):
    if not platform_manager[state['platform']].has_target or 'id' in state:
        return
    await bot.send(event=event, message='请输入订阅用户的id，详情查阅https://github.com/felinae98/nonebot-hk-reporter')
    await add_sub.pause()

@add_sub.handle()
async def add_sub_parse_id(bot: Bot, event: Event, state: T_State):
    if not platform_manager[state['platform']].has_target or 'id' in state:
        return
    target = str(event.get_message()).strip()
    name = await check_sub_target(state['platform'], target)
    if not name:
        await add_sub.reject('id输入错误')
    state['id'] = target
    state['name'] = name

@add_sub.handle()
async def add_sub_handle_cat(bot: Bot, event: Event, state: T_State):
    if not platform_manager[state['platform']].categories:
        return
    if 'cats' in state:
        return
    await bot.send(event=event, message='请输入要订阅的类别，以空格分隔，支持的类别有：{}'.format(
            ','.join(list(platform_manager[state['platform']].categories.values()))
        ))
    await add_sub.pause()

@add_sub.handle()
async def add_sub_parse_cat(bot: Bot, event: Event, state: T_State):
    if not platform_manager[state['platform']].categories:
        return
    if 'cats' in state:
        return
    res = []
    for cat in str(event.get_message()).strip().split():
        if cat not in platform_manager[state['platform']].reverse_category:
            await add_sub.reject('不支持 {}'.format(cat))
        res.append(platform_manager[state['platform']].reverse_category[cat])
    state['cats'] = res

@add_sub.handle()
async def add_sub_handle_tag(bot: Bot, event: Event, state: T_State):
    if not platform_manager[state['platform']].enable_tag:
        return
    if 'tags' in state:
        return
    await bot.send(event=event, message='请输入要订阅的tag，订阅所有tag输入"全部标签"')
    await add_sub.pause()

@add_sub.handle()
async def add_sub_parse_tag(bot: Bot, event: Event, state: T_State):
    if not platform_manager[state['platform']].enable_tag:
        return
    if 'tags' in state:
        return
    if str(event.get_message()).strip() == '全部标签':
        state['tags'] = []
    else:
        state['tags'] = str(event.get_message()).strip().split()

@add_sub.handle()
async def add_sub_process(bot: Bot, event: GroupMessageEvent, state: T_State):
    if not platform_manager[state['platform']].has_target:
        state['name'] = await platform_manager[state['platform']].get_account_name(Target(''))
        state['id'] = 'default'
    config = Config()
    config.add_subscribe(event.group_id, user_type='group',
            target=state['id'],
            target_name=state['name'], target_type=state['platform'],
            cats=state.get('cats', []), tags=state.get('tags', []))
    await add_sub.finish('添加 {} 成功'.format(state['name']))

query_sub = on_command("查询订阅", rule=to_me(), priority=5)
@query_sub.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    config: Config = Config()
    sub_list = config.list_subscribe(event.group_id, "group")
    res = '订阅的帐号为：\n'
    for sub in sub_list:
        res += '{} {} {}'.format(sub['target_type'], sub['target_name'], sub['target'])
        platform = platform_manager[sub['target_type']]
        if platform.categories:
            res += ' [{}]'.format(', '.join(map(lambda x: platform.categories[x], sub['cats'])))
        if platform.enable_tag:
            res += ' {}'.format(', '.join(sub['tags']))
        res += '\n'
    # send_msgs(bot, event.group_id, 'group', [await parse_text(res)])
    await query_sub.finish(Message(await parse_text(res)))

del_sub = on_command("删除订阅", rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER, priority=5)
@del_sub.handle()
async def send_list(bot: Bot, event: GroupMessageEvent, state: T_State):
    config: Config = Config()
    sub_list = config.list_subscribe(event.group_id, "group")
    res = '订阅的帐号为：\n'
    state['sub_table'] = {}
    for index, sub in enumerate(sub_list, 1):
        state['sub_table'][index] = {'target_type': sub['target_type'], 'target': sub['target']}
        res += '{} {} {} {}\n'.format(index, sub['target_type'], sub['target_name'], sub['target'])
        platform = platform_manager[sub['target_type']]
        if platform.categories:
            res += ' [{}]'.format(', '.join(map(lambda x: platform.categories[x], sub['cats'])))
        if platform.enable_tag:
            res += ' {}'.format(', '.join(sub['tags']))
        res += '\n'
    res += '请输入要删除的订阅的序号'
    await bot.send(event=event, message=Message(await parse_text(res)))

@del_sub.receive()
async def do_del(bot, event: GroupMessageEvent, state: T_State):
    try:
        index = int(str(event.get_message()).strip())
        config = Config()
        config.del_subscribe(event.group_id, 'group', **state['sub_table'][index])
    except Exception as e:
        await del_sub.reject('删除错误')
        logger.warning(e)
    else:
        await del_sub.finish('删除成功')
