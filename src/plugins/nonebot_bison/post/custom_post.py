from dataclasses import dataclass

from nonebot.adapters.onebot.v11.message import Message, MessageSegment

from .abstract_post import AbstractPost, BasePost


@dataclass
class _CustomPost(BasePost):

    message_segments: list[MessageSegment]

    async def generate_text_messages(self) -> list[MessageSegment]:
        return self.message_segments

    async def generate_pic_messages(self) -> list[MessageSegment]:
        ...  # TODO


@dataclass
class CustomPost(_CustomPost, AbstractPost):
    ...
