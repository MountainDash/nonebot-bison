import logging

import nonebot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from nonebot import get_driver
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.log import LoguruHandler, logger

from .config import config
from .platform import platform_manager
from .plugin_config import plugin_config
from .send import do_send_msgs, send_msgs
from .types import UserSubInfo

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


@get_driver().on_startup
async def _start():
    for platform_name, platform in platform_manager.items():
        if platform.schedule_type in ["cron", "interval", "date"]:
            logger.info(
                f"start scheduler for {platform_name} with {platform.schedule_type} {platform.schedule_kw}"
            )
            scheduler.add_job(
                fetch_and_send,
                platform.schedule_type,
                **platform.schedule_kw,
                args=(platform_name,),
            )

    scheduler.configure({"apscheduler.timezone": "Asia/Shanghai"})
    scheduler.start()


# get_driver().on_startup(_start)


async def fetch_and_send(target_type: str):
    target = config.get_next_target(target_type)
    if not target:
        return
    logger.debug(
        "try to fecth new posts from {}, target: {}".format(target_type, target)
    )
    send_user_list = config.target_user_cache[target_type][target]
    send_userinfo_list = list(
        map(
            lambda user: UserSubInfo(
                user,
                lambda target: config.get_sub_category(
                    target_type, target, user.user_type, user.user
                ),
                lambda target: config.get_sub_tags(
                    target_type, target, user.user_type, user.user
                ),
            ),
            send_user_list,
        )
    )
    to_send = await platform_manager[target_type].do_fetch_new_post(
        target, send_userinfo_list
    )
    if not to_send:
        return
    bot = nonebot.get_bot()
    assert isinstance(bot, Bot)
    for user, send_list in to_send:
        for send_post in send_list:
            logger.info("send to {}: {}".format(user, send_post))
            if not bot:
                logger.warning("no bot connected")
            else:
                await send_msgs(
                    bot, user.user, user.user_type, await send_post.generate_messages()
                )


class CustomLogHandler(LoguruHandler):
    def filter(self, record: logging.LogRecord):
        return record.msg != (
            'Execution of job "%s" '
            "skipped: maximum number of running instances reached (%d)"
        )


if plugin_config.bison_use_queue:
    scheduler.add_job(do_send_msgs, "interval", seconds=0.3, coalesce=True)

    aps_logger = logging.getLogger("apscheduler")
    aps_logger.setLevel(30)
    aps_logger.handlers.clear()
    aps_logger.addHandler(CustomLogHandler())
