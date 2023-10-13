from typing import TYPE_CHECKING, Literal

from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from nonebot_bison.theme import AbstractTheme

if TYPE_CHECKING:
    from nonebot_bison.post import Post


class BasicTheme(AbstractTheme):
    """最基本的主题

    纯文本，应为每个Post必定支持的Theme
    """

    name: Literal["basic"] = "basic"

    async def render(self, post: "Post") -> list[MessageSegmentFactory]:
        text = ""

        if post.title:
            text += f"{post.title}\n\n"

        text += post.content if len(post.content) < 500 else f"{post.content[:500]}..."

        text += f"来源: {post.paltform_name} {post.nickname or ''}\n"

        if post.url:
            text += f"详情: {post.url}"

        msgs: list[MessageSegmentFactory] = [Text(text)]
        if post.images:
            msgs.extend(map(Image, post.images))

        return msgs
