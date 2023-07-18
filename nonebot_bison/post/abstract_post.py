from functools import reduce
from abc import ABC, abstractmethod

from pydantic import Field, BaseModel
from nonebot_plugin_saa import MessageFactory, MessageSegmentFactory


class AbstractPost(ABC, BaseModel):
    compress: bool = False
    extra_msg: list[MessageFactory] = Field(default_factory=list)

    @abstractmethod
    async def generate(self) -> list[MessageSegmentFactory]:
        "Generate MessageFactory list from this instance"
        ...

    async def generate_messages(self) -> list[MessageFactory]:
        "really call to generate messages"
        msg_segments = await self.generate()
        if msg_segments:
            if self.compress:
                msgs = [reduce(lambda x, y: x.append(y), msg_segments, MessageFactory([]))]
            else:
                msgs = [MessageFactory([msg_segment]) for msg_segment in msg_segments]
        else:
            msgs = []
        msgs.extend(self.extra_msg)
        return msgs
