from typing import Literal

from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from nonebot_bison.types import PostHeader, PostPayload
from nonebot_bison.utils import pic_merge, is_pics_mergable
from nonebot_bison.theme import Theme, ThemeRenderUnsupportError


class BriefTheme(Theme):
    """简报主题，只发送标题、头图（如果有）、URL（如果有）"""

    name: Literal["brief"] = "brief"

    async def render(self, header: PostHeader, payload: PostPayload) -> list[MessageSegmentFactory]:
        if not payload.title:
            raise ThemeRenderUnsupportError("Post has no title")
        text = f"{payload.title}\n\n"
        text += f"来源: {payload.platform} {payload.author or ''}\n"
        if payload.url:
            text += f"详情: {payload.url}"

        msgs: list[MessageSegmentFactory] = [Text(text)]
        if payload.images:
            pics = payload.images
            if is_pics_mergable(pics):
                pics = await pic_merge(list(pics), header.http_client)
            msgs.append(Image(pics[0]))

        return msgs
