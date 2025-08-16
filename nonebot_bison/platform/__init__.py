from collections import defaultdict
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from typing import TYPE_CHECKING

import anyio

from nonebot_bison.courier import Courier, Parcel, post_to_courier
from nonebot_bison.plugin_config import plugin_config
from nonebot_bison.post import Post, SendableMessages
from nonebot_bison.types import SubUnitPayload
from nonebot_bison.utils.context import ProcessContext

from .platform import Platform, make_no_target_group

if TYPE_CHECKING:
    from nonebot_bison.utils.site import ClientManager

_package_dir = str(Path(__file__).resolve().parent)
for _, module_name, _ in iter_modules([_package_dir]):
    import_module(f"{__name__}.{module_name}")


_platform_list: defaultdict[str, list[type[Platform]]] = defaultdict(list)
for _platform in Platform.registry:
    if not _platform.enabled:
        continue
    _platform_list[_platform.platform_name].append(_platform)

platform_manager: dict[str, type[Platform]] = {}
for name, platform_list in _platform_list.items():
    if len(platform_list) == 1:
        platform_manager[name] = platform_list[0]
    else:
        platform_manager[name] = make_no_target_group(platform_list)


def _get_unavailable_platforms() -> dict[str, str]:
    res = {}
    for name, platform in platform_manager.items():
        if platform.site.require_browser and not plugin_config.bison_use_browser:
            res[name] = "需要启用 bison_use_browser"
    return res


# platform => reason for not available
unavailable_paltforms: dict[str, str] = _get_unavailable_platforms()


@Courier.receive_from("schedule")
async def handle_schedule(parcel: Parcel[SubUnitPayload]):
    if parcel.metadata is None:
        raise parcel.DeliveryReject("Parcel metadata cannot be None")
    elif "platform_name" not in parcel.metadata:
        raise parcel.DeliveryReject("Parcel metadata must contain 'platform_name'")
    elif "client_mgr" not in parcel.metadata:
        raise parcel.DeliveryReject("Parcel metadata must contain 'client_mgr'")

    platform_name = parcel.metadata["platform_name"]
    if platform_name not in platform_manager:
        raise parcel.DeliveryReject(f"Platform {platform_name} is not registered")

    client_mgr: ClientManager = parcel.metadata["client_mgr"]

    platform = platform_manager[platform_name]
    if not platform.enabled:
        raise parcel.DeliveryReject(f"Platform {platform_name} is not enabled")

    context = ProcessContext(client_mgr)
    platform_obj = platform_manager[platform_name](context)

    if isinstance(parcel.payload, list):
        to_send = await platform_obj.do_batch_fetch_new_post(parcel.payload)
    else:
        to_send = await platform_obj.do_fetch_new_post(parcel.payload)

    # 限制最大并发渲染数
    semaphore = anyio.Semaphore(plugin_config.bison_max_concurrency.render_post)

    for user, post_list in to_send:
        results: list[SendableMessages] = []

        async def _render(semaphore: anyio.Semaphore, post: Post):
            async with semaphore:
                rendered_post = await post.generate_messages()
                results.append(rendered_post)

        async with anyio.create_task_group() as tg:
            for post in post_list:
                tg.start_soon(_render, semaphore, post)

        await post_to_courier(
            Parcel(
                tag="message",
                payload=results,
                metadata={"send_to": user},
            )
        )
