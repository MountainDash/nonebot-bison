from typing import cast

from nonebot import logger
from nonebot_plugin_saa import Text, MessageFactory, MessageSegmentFactory

from nonebot_bison.theme import theme_manager
from nonebot_bison.utils import text_to_image
from nonebot_bison.plugin_config import plugin_config
from nonebot_bison.types import (
    Parcel,
    PostHeader,
    ParcelLabel,
    PostPayload,
    MessageHeader,
    MessagePayload,
    ThemeRenderError,
    ThemeRenderUnsupportError,
)

from .conveyor import Conveyor
from .registry import DefaultConveyor, conveyor_dispatch


def get_config_theme(platform_code: str) -> str | None:
    """获取用户指定的theme"""
    return plugin_config.bison_platform_theme.get(platform_code)


def get_theme_priority_list(header: PostHeader):
    """获取渲染所使用的theme名列表，按照优先级排序"""
    themes_by_priority: list[str] = []
    # 最先使用用户指定的theme
    if user_theme := get_config_theme(header.platform_code):
        themes_by_priority.append(user_theme)
    # 然后使用平台默认的theme
    if header.recommend_theme not in themes_by_priority:
        themes_by_priority.append(header.recommend_theme)
    # 最后使用最基础的theme
    if "basic" not in themes_by_priority:
        themes_by_priority.append("basic")
    return themes_by_priority


async def theme_render(
    header: PostHeader, payload: PostPayload, theme_priority_list: list[str]
) -> list[MessageSegmentFactory]:
    """按照 Theme 优先级列表渲染 Post，返回 MessageSegmentFactory 列表"""
    for theme_name in theme_priority_list:
        if theme := theme_manager[theme_name]:
            try:
                logger.debug(f"rendering post with theme {theme_name}")
                return await theme.do_render(header, payload)
            except ThemeRenderUnsupportError as e:
                logger.warning(f"Theme {theme_name} does not support Post of {header.platform_code}: {e}")
                continue
            except ThemeRenderError as e:
                logger.exception(f"Theme {theme_name} render error: {e}")
                continue
        else:
            logger.error(f"Theme {theme_name} not found")
            continue
    else:
        raise ThemeRenderError(f"No theme can render Post of {header.platform_code}")


async def render_post_process(header: PostHeader, msg_segments: list[MessageSegmentFactory]) -> list[MessageFactory]:
    """对渲染后的 MessageSegmentFactory 列表进行处理"""

    async def convert(msg: MessageSegmentFactory) -> MessageSegmentFactory:
        if isinstance(msg, Text):
            return await text_to_image(msg)
        else:
            return msg

    if plugin_config.bison_use_pic:
        msg_segments = [await convert(msg) for msg in msg_segments]

    if header.compress:
        msgs = [MessageFactory(msg_segments)]
    else:
        msgs = [MessageFactory(msg_segment) for msg_segment in msg_segments]

    return msgs


async def do_render(post: Parcel) -> Parcel:
    """渲染 Post，返回 Parcel"""
    assert post.header.label == ParcelLabel.POST
    post_header = cast(PostHeader, post.header)
    post_payload = cast(PostPayload, post.payload)
    target = post_header.send_target
    assert target

    themes_by_priority = get_theme_priority_list(post_header)
    logger.debug(f"themes_by_priority: {themes_by_priority}")

    unprocessed_payload = await theme_render(post_header, post_payload, themes_by_priority)
    processed_payload = await render_post_process(post_header, unprocessed_payload)

    logger.info(f"send to {target}: {processed_payload}")  # TODO: post 的 __str__ 方法，避免 bytes 刷屏
    return Parcel(
        MessageHeader(target=target),
        MessagePayload(
            content=processed_payload,
        ),
    )


@conveyor_dispatch(DefaultConveyor.RENDER, ParcelLabel.POST)
async def post_render(parcel: Parcel):
    """渲染 Post"""
    msg_parcel = await do_render(parcel)
    await Conveyor.put_to(DefaultConveyor.SEND, msg_parcel)
