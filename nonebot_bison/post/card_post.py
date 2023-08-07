from dataclasses import field, dataclass

from nonebot.log import logger
from pydantic import BaseModel
from nonebot_plugin_saa import Image, MessageSegmentFactory

from .abstract_post import AbstractPost
from ..cards import ThemeMetadata, card_manager


@dataclass
class CardPost(AbstractPost):
    """额外的文本请考虑extra_msg"""

    theme: str
    card_data: BaseModel
    pics: list[str | bytes] = field(default_factory=list)

    _card_meta: ThemeMetadata | None = field(init=False, default=None)

    @property
    def card_meta(self):
        if not self._card_meta:
            self._card_meta = card_manager[self.theme]

        return self._card_meta

    async def _render_card(self):
        if not isinstance(self.card_data, self.card_meta.schemas):
            logger.error("data schemas NOT match card theme")
            return b""

        return await self.card_meta.render(self.card_data)

    async def generate(self) -> list[MessageSegmentFactory]:
        msg_segments: list[MessageSegmentFactory] = []
        msg_segments.append(Image(await self._render_card()))

        for pic in self.pics:
            msg_segments.append(Image(pic))

        return msg_segments
