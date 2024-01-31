from typing import Literal

from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from nonebot_bison.theme import Theme
from nonebot_bison.types import PostHeader, PostPayload
from nonebot_bison.utils import pic_merge, is_pics_mergable


class BasicTheme(Theme):
    """最基本的主题

    纯文本，应为每个Post必定支持的Theme
    """

    name: Literal["basic"] = "basic"

    async def render(self, header: PostHeader, payload: PostPayload) -> list[MessageSegmentFactory]:
        text = ""

        if payload.title:
            text += f"{payload.title}\n\n"

        text += payload.content if len(payload.content) < 500 else f"{payload.content[:500]}..."

        text += f"\n来源: {payload.platform} {payload.author or ''}\n"

        if payload.url:
            text += f"详情: {payload.url}"

        msgs: list[MessageSegmentFactory] = [Text(text)]
        if payload.images:
            pics = payload.images
            if is_pics_mergable(pics):
                pics = await pic_merge(list(pics), header.http_client)
            msgs.extend(map(Image, pics))

        return msgs
