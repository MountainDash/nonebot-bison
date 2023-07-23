from pydantic import Field
import nonebot_plugin_saa as saa
from nonebot_plugin_saa.utils import MessageSegmentFactory

from .utils import pic_merge
from ..utils import text_to_saa
from .abstract_post import AbstractPost
from ..plugin_config import plugin_config


class BasePost(AbstractPost):
    """所有平台都应该支持的Post类型"""

    platform: str
    text: str
    url: str | None = None
    target_name: str | None = None
    pics: list[str | bytes] = Field(default_factory=list)

    message: list[MessageSegmentFactory] | None = None

    async def generate(self) -> list[MessageSegmentFactory]:
        if self.message is None:
            self.pics = await pic_merge(self.pics)
            msg_segments: list[MessageSegmentFactory] = []
            text = ""
            if self.text:
                text += "{}".format(self.text if len(self.text) < 500 else self.text[:500] + "...")
            if text:
                text += "\n"
            text += f"来源: {self.platform}"
            if self.target_name:
                text += f" {self.target_name}"
            if self.url:
                text += f" \n详情: {self.url}"
            msg_segments.append(saa.Text(text))
            for pic in self.pics:
                msg_segments.append(saa.Image(pic))
            self.message = msg_segments
        return self.message

    def __str__(self):
        return "type: {}\nfrom: {}\ntext: {}\nurl: {}\npic: {}".format(
            self.platform,
            self.target_name,
            self.text if len(self.text) < 500 else self.text[:500] + "...",
            self.url,
            ", ".join("b64img" if isinstance(x, bytes) or x.startswith("base64") else x for x in self.pics),
        )


class PlainPost(BasePost):
    """最基本的Post, 支持简单的文转图"""

    pic_message: list[MessageSegmentFactory] | None = None

    async def _text_to_img(self) -> list[MessageSegmentFactory]:
        if self.pic_message is None:
            self.pics = await pic_merge(self.pics)
            msg_segments: list[MessageSegmentFactory] = []
            text = ""
            if self.text:
                text += f"{self.text}"
                text += "\n"
            text += f"来源: {self.platform}"
            if self.target_name:
                text += f" {self.target_name}"
            msg_segments.append(await text_to_saa(text))
            if not self.platform == "rss" and self.url:
                msg_segments.append(saa.Text(self.url))
            for pic in self.pics:
                msg_segments.append(saa.Image(pic))
            self.pic_message = msg_segments
        return self.pic_message

    async def generate(self) -> list[MessageSegmentFactory]:
        if plugin_config.bison_use_pic:
            return await self._text_to_img()
        else:
            return await super().generate()
