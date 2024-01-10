import anyio
from nonebot import logger

from ..delivery.render import post_render
from ..delivery.send import parcel_deliver
from .render import render_dispatch as render_dispatch


async def init_delivery():
    logger.info("init delivery")

    async with anyio.create_task_group() as tg:
        tg.start_soon(post_render)
        logger.info("post render deque started")
        tg.start_soon(parcel_deliver)
        logger.info("parcel deliver deque started")


__all__ = [
    "render_dispatch",
    "init_delivery",
]
