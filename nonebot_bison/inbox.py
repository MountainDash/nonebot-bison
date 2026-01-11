import anyio
from anyio.abc import TaskGroup
from nonebot import logger

from nonebot_bison.core.courier import Courier, Parcel, post_to_courier
from nonebot_bison.core.platform import CompletedPlatform, Platform
from nonebot_bison.core.post import Post
from nonebot_bison.core.schedule import SubUnits
from nonebot_bison.core.site import ClientManager, ProcessContext
from nonebot_bison.core.theme import (
    ThemeRenderError,
    ThemeRenderUnsupportError,
    theme_manager,
)
from nonebot_bison.core.theme.utils import get_priority_themes
from nonebot_bison.setting import plugin_config


@Courier.receive_from("schedule")
async def handle_schedule(tg: TaskGroup, parcel: Parcel[SubUnits]):
    if parcel.metadata is None:
        raise parcel.DeliveryReject("Parcel metadata cannot be None")
    elif "platform_name" not in parcel.metadata:
        raise parcel.DeliveryReject("Parcel metadata must contain 'platform_name'")
    elif "client_mgr" not in parcel.metadata:
        raise parcel.DeliveryReject("Parcel metadata must contain 'client_mgr'")

    platform_name: str = parcel.metadata["platform_name"]
    if platform_name not in Platform.registry:
        raise parcel.DeliveryReject(f"Platform {platform_name} is not registered")

    client_mgr: ClientManager = parcel.metadata["client_mgr"]

    platform: Platform = Platform.registry[platform_name]
    if not platform.platform_config.enable:
        raise parcel.DeliveryReject(f"Platform {platform_name} is not enabled")

    context = ProcessContext(client_mgr)
    platform_obj: CompletedPlatform = Platform.registry[platform_name](context)

    to_send = await platform_obj.fetch(parcel.payload)  # type: ignore[reportArgumentType] 这里会自动分配

    # 限制最大并发渲染数
    semaphore = anyio.Semaphore(plugin_config.bison_render_post_concurrency)

    for user, post_list in to_send:

        async def _render(semaphore: anyio.Semaphore, post: Post):
            themes = get_priority_themes(post.platform)
            for theme_name in themes:
                if theme := theme_manager[theme_name]:
                    try:
                        async with semaphore:
                            parcel = await theme.package(post, {"send_to": user})
                            await post_to_courier(parcel)
                    except ThemeRenderUnsupportError as e:
                        logger.warning(
                            f"Theme {theme_name} does not support Post of {platform_obj.__class__.__name__}: {e}"
                        )
                        continue
                    except ThemeRenderError as e:
                        logger.exception(f"Theme {theme_name} render error: {e}")
                        continue
                else:
                    logger.error(f"Theme {theme_name} not found")
                    continue
            else:
                raise ThemeRenderError(
                    f"No theme can render Post of {platform_obj.__class__.__name__}"
                )

        for post in post_list:
            tg.start_soon(_render, semaphore, post)
