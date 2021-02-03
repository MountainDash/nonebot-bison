import time
import asyncio
from collections import defaultdict
from .weibo import Weibo, get_user_info as weibo_user_info
from .bilibili import get_user_info as bilibili_user_info
from .rss import get_rss_info as rss_info

async def check_sub_target(target_type, target):
    if target_type == 'weibo':
        return await weibo_user_info(target)
    elif target_type == 'bilibili':
        return await bilibili_user_info(target)
    elif target_type == 'rss':
        return await rss_info(target)
    else:
        return None


scheduler_last_run = defaultdict(lambda: 0)
async def scheduler(fun, target_type):
    platform_interval = {
            'weibo': 3
        }
    if (wait_time := time.time() - scheduler_last_run[target_type]) < platform_interval[target_type]:
        await asyncio.sleep(wait_time)
    await fun()
