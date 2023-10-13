from functools import reduce
from dataclasses import dataclass
from abc import ABC, abstractmethod

from nonebot_plugin_saa import MessageFactory, MessageSegmentFactory


@dataclass(kw_only=True)
class AbstractPost(ABC):
    compress: bool = False
    extra_msg: list[MessageFactory] | None = None

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

        if self.extra_msg:
            msgs.extend(self.extra_msg)

        return msgs
