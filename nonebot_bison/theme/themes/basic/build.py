from typing import TYPE_CHECKING, Literal

from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from nonebot_bison.theme import Theme
from nonebot_bison.utils import pic_merge, is_pics_mergable

if TYPE_CHECKING:
    from nonebot_bison.post import Post


class BasicTheme(Theme):
    """最基本的主题

    纯文本，应为每个Post必定支持的Theme
    """

    name: Literal["basic"] = "basic"

    async def render(self, post: "Post") -> list[MessageSegmentFactory]:
        text = ""

        text += f"{post.title}\n\n" if post.title else ""

        text += post.content if len(post.content) < 500 else f"{post.content[:500]}..."

        if rp := post.repost:
            text += f"\n--------------\n转发自 {rp.nickname or ''}:\n"
            text += f"{rp.title}\n\n" if rp.title else ""
            text += rp.content if len(rp.content) < 500 else f"{rp.content[:500]}..."

        text += "\n--------------\n"

        text += f"来源: {post.platform.name} {post.nickname or ''}\n"

        urls: list[str] = []
        if rp and rp.url:
            urls.append(f"转发详情：{rp.url}")
        if post.url:
            urls.append(f"详情: {post.url}")

        if urls:
            text += "\n".join(urls)

        msgs: list[MessageSegmentFactory] = [Text(text)]
        if post.images:
            pics = post.images
            if is_pics_mergable(pics):
                pics = await pic_merge(list(pics), post.platform.client)
            msgs.extend(map(Image, pics))

        return msgs
