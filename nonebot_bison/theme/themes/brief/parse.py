from typing import TYPE_CHECKING, Literal

from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

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
            msgs.extend(map(Image, post.images))
        if post.url:
            msgs.append(Text(post.url))

        return msgs
