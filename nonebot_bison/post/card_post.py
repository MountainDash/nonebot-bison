from typing import Any

from pydantic import Field, ValidationError
from nonebot_plugin_saa import Image, MessageSegmentFactory

from .abstract_post import AbstractPost
from .cards import ThemeMetadata, card_manager


class CardPost(AbstractPost):
    theme: str
    card_data: dict[str, Any]
    pics: list[str | bytes] = Field(default_factory=list)
    _card_meta: ThemeMetadata | None = None

    @property
    def card_meta(self):
        if not self._card_meta:
            card = card_manager.get(self.theme)
            self._card_meta = card

        return self._card_meta

    async def _check_card_data(self):
        card_meta = self.card_meta

        try:
            crad_data = card_meta.schema.parse_obj(self.card_data)
        except ValidationError as e:
            raise e
        else:
            return crad_data

    async def _render_card(self):
        card_data = await self._check_card_data()

        return await self.card_meta.render(card_data)

    async def generate(self) -> list[MessageSegmentFactory]:
        msg_segments = []
        msg_segments.append(await self._render_card())
        for pic in self.pics:
            msg_segments.append(Image(pic))
        return msg_segments
