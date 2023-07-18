from nonebot import logger
import nonebot_plugin_saa as saa
from nonebot_plugin_saa.utils import MessageSegmentFactory

from ..utils import parse_text
from .base_post import BasePost


class PlainPost(BasePost):
    """最基本的Post, 支持简单的文转图"""

    async def _generate(self) -> list[MessageSegmentFactory]:
        if self._pic_message is None:
            await self._pic_merge()
            msg_segments: list[MessageSegmentFactory] = []
            text = ""
            if self.text:
                text += f"{self.text}"
                text += "\n"
            text += f"来源: {self.target_type}"
            if self.target_name:
                text += f" {self.target_name}"
            msg_segments.append(await parse_text(text))
            if not self.target_type == "rss" and self.url:
                msg_segments.append(saa.Text(self.url))
            for pic in self.pics:
                msg_segments.append(saa.Image(pic))
            self._pic_message = msg_segments
        return self._pic_message

    async def generate(self) -> list[MessageSegmentFactory]:
        try:
            return await self._generate()
        except Exception as e:
            logger.error(f"调用PicPost.generate()时出现错误: {repr(e)}, 尝试使用BasePost.generate()")
            return await super().generate()
