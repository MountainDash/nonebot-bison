from typing import TYPE_CHECKING, Literal

from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from nonebot_bison.utils import pic_merge, is_pics_mergable
from nonebot_bison.theme import AbstractTheme, ThemeRenderUnsupportError

if TYPE_CHECKING:
    from nonebot_bison.post import Post


class BriefTheme(AbstractTheme):
    """简报主题，只发送标题、头图（如果有）、URL（如果有）"""

    name: Literal["brief"] = "brief"

    async def render(self, post: "Post") -> list[MessageSegmentFactory]:
        if not post.title:
            raise ThemeRenderUnsupportError("Post has no title")

        msgs: list[MessageSegmentFactory] = [Text(post.title)]
        if post.images:
            pics = post.images
            if is_pics_mergable(pics):
                pics = await pic_merge(list(pics), post.platform.client)
            msgs.append(Image(pics[0]))
        if post.url:
            msgs.append(Text(post.url))

        return msgs
