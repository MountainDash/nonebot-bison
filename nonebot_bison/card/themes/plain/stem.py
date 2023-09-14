from nonebot_plugin_saa import Text
from nonebot_plugin_saa.utils import MessageSegmentFactory

from ...types import BaseStem
from ....utils import parse_text
from ....plugin_config import plugin_config


class Stem(BaseStem):
    platform: str
    text: str
    url: str | None = None
    target_name: str | None = None
    override_text_to_pic: bool = False

    @classmethod
    def get_theme_name(cls):
        return "plain"

    async def render(self):
        if self.use_pic:
            return await self.generate_pic_messages()

        return await self.generate_text_messages()

    @property
    def use_pic(self):
        if self.override_text_to_pic:
            return True
        return plugin_config.bison_use_pic

    async def generate_text_messages(self) -> Text:
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
        return Text(text)

    async def generate_pic_messages(self) -> list[MessageSegmentFactory]:
        msg_segments: list[MessageSegmentFactory] = []
        text = ""
        if self.text:
            text += f"{self.text}"
            text += "\n"
        text += f"来源: {self.platform}"
        if self.target_name:
            text += f" {self.target_name}"
        msg_segments.append(await parse_text(text, force_pic=True))
        if not self.platform == "rss" and self.url:
            msg_segments.append(Text(self.url))
        return msg_segments

    def __str__(self):
        return "type: {}\nfrom: {}\ntext: {}\nurl: {}".format(
            self.platform, self.target_name, self.text if len(self.text) < 500 else self.text[:500] + "...", self.url
        )
