from dataclasses import dataclass
from abc import ABC, abstractmethod

from nonebot_plugin_saa import Text, MessageFactory, MessageSegmentFactory

from ..utils import text_to_image
from ..plugin_config import plugin_config


@dataclass(kw_only=True)
class AbstractPost(ABC):
    compress: bool = False
    extra_msg: list[MessageFactory] | None = None

    @abstractmethod
    async def generate(self) -> list[MessageSegmentFactory]:
        "Generate MessageSegmentFactory list from this instance"
        ...

    async def generate_messages(self) -> list[MessageFactory]:
        "really call to generate messages"
        msg_segments = await self.generate()
        msg_segments = await self.message_segments_process(msg_segments)
        msgs = await self.message_process(msg_segments)
        return msgs

    async def message_segments_process(self, msg_segments: list[MessageSegmentFactory]) -> list[MessageSegmentFactory]:
        "generate message segments and process them"

        async def convert(msg: MessageSegmentFactory) -> MessageSegmentFactory:
            if isinstance(msg, Text):
                return await text_to_image(msg)
            else:
                return msg

        if plugin_config.bison_use_pic:
            return [await convert(msg) for msg in msg_segments]

        return msg_segments

    async def message_process(self, msg_segments: list[MessageSegmentFactory]) -> list[MessageFactory]:
        "generate messages and process them"
        if self.compress:
            msgs = [MessageFactory(msg_segments)]
        else:
            msgs = [MessageFactory(msg_segment) for msg_segment in msg_segments]

        if self.extra_msg:
            msgs.extend(self.extra_msg)

        return msgs
