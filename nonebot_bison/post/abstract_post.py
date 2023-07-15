from functools import reduce
from abc import abstractmethod
from dataclasses import field, dataclass

from nonebot_plugin_saa import MessageFactory, MessageSegmentFactory

from ..plugin_config import plugin_config


@dataclass
class BasePost:
    @abstractmethod
    async def generate_text_messages(self) -> list[MessageSegmentFactory]:
        "Generate MessageFactory list from this instance"
        ...

    @abstractmethod
    async def generate_pic_messages(self) -> list[MessageSegmentFactory]:
        "Generate MessageFactory list from this instance with `use_pic`"
        ...


@dataclass
class OptionalMixin:
    # Because of https://stackoverflow.com/questions/51575931/class-inheritance-in-python-3-7-dataclasses

    override_use_pic: bool | None = None
    compress: bool = False
    extra_msg: list[MessageFactory] = field(default_factory=list)

    def _use_pic(self):
        if self.override_use_pic is not None:
            return self.override_use_pic
        return plugin_config.bison_use_pic


@dataclass
class AbstractPost(OptionalMixin, BasePost):
    async def generate_messages(self) -> list[MessageFactory]:
        if self._use_pic():
            msg_segments = await self.generate_pic_messages()
        else:
            msg_segments = await self.generate_text_messages()
        if msg_segments:
            if self.compress:
                msgs = [reduce(lambda x, y: x.append(y), msg_segments, MessageFactory([]))]
            else:
                msgs = [MessageFactory([msg_segment]) for msg_segment in msg_segments]
        else:
            msgs = []
        msgs.extend(self.extra_msg)
        return msgs
