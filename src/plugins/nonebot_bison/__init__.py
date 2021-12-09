import nonebot

from . import config_manager
from . import config
from . import scheduler
from . import send
from . import post
from . import platform
from . import types
from . import utils
from . import admin_page

__help__version__ = '0.4.3'
__help__plugin__name__ = 'nonebot_bison'
__usage__ = ('本bot可以提供b站、微博等社交媒体的消息订阅，详情'
        '请查看本bot文档，或者at本bot发送“添加订阅”订阅第一个帐号')
