from typing import TYPE_CHECKING, Literal

from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from nonebot_bison.utils import pic_merge, is_pics_mergable
from nonebot_bison.theme import Theme, ThemeRenderUnsupportError

if TYPE_CHECKING:
    from nonebot_bison.post import Post


class BriefTheme(Theme):
    """简报主题，只发送标题、头图（如果有）、URL（如果有）"""

    name: Literal["brief"] = "brief"

    async def render(self, post: "Post") -> list[MessageSegmentFactory]:
        if not post.title:
            raise ThemeRenderUnsupportError("Post has no title")
        text = f"{post.title}\n\n"
        text += f"来源: {post.platform.name} {post.nickname or ''}{' 的转发' if post.repost else ''}\n"

        urls: list[str] = []
        if (rp := post.repost) and rp.url:
            urls.append(f"转发详情: {rp.url}")
        if post.url:
            urls.append(f"详情: {post.url}")

        if urls:
            text += "\n".join(urls)

        msgs: list[MessageSegmentFactory] = [Text(text)]
        if post.images:
            pics = post.images
            if is_pics_mergable(pics):
                pics = await pic_merge(list(pics), post.platform.client)
            msgs.append(Image(pics[0]))

        return msgs
