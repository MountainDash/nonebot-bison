from io import BytesIO
from dataclasses import field, dataclass

from nonebot.log import logger
from PIL import Image as PILImage
from nonebot_plugin_saa import Image, MessageSegmentFactory

from ..utils import http_client
from .abstract_post import AbstractPost
from ..card import BaseStem, ThemeMetadata, card_manager


@dataclass
class Post(AbstractPost):
    """额外的文本请考虑extra_msg"""

    card_data: BaseStem
    pics: list[str | bytes] = field(default_factory=list)
    theme: str | None = None
    """显式指定theme，不指定则使用card_data的theme"""

    _card_meta: ThemeMetadata | None = field(init=False, default=None)

    @property
    def post_theme(self) -> str:
        return self.theme or self.card_data.get_theme_name()

    @property
    def card_meta(self):
        if not self._card_meta:
            self._card_meta = card_manager[self.post_theme]

        return self._card_meta

    async def _render_card(self) -> list[MessageSegmentFactory] | MessageSegmentFactory:
        if not isinstance(self.card_data, self.card_meta.stem):
            logger.error("data schemas NOT match card theme")
            raise TypeError("data schemas NOT match card theme")

        return await self.card_data.render()

    async def generate(self) -> list[MessageSegmentFactory]:
        msg_segments: list[MessageSegmentFactory] = []
        render_result = await self._render_card()
        if isinstance(render_result, list):
            msg_segments.extend(render_result)
        else:
            msg_segments.append(render_result)

        await self._pic_merge()
        for pic in self.pics:
            msg_segments.append(Image(pic))

        return msg_segments

    async def _pic_url_to_image(self, data: str | bytes) -> PILImage.Image:
        pic_buffer = BytesIO()
        if isinstance(data, str):
            async with http_client() as client:
                res = await client.get(data)
            pic_buffer.write(res.content)
        else:
            pic_buffer.write(data)
        return PILImage.open(pic_buffer)

    def _check_image_square(self, size: tuple[int, int]) -> bool:
        return abs(size[0] - size[1]) / size[0] < 0.05

    async def _pic_merge(self) -> None:
        if len(self.pics) < 3:
            return
        first_image = await self._pic_url_to_image(self.pics[0])
        if not self._check_image_square(first_image.size):
            return
        images: list[PILImage.Image] = [first_image]
        # first row
        for i in range(1, 3):
            cur_img = await self._pic_url_to_image(self.pics[i])
            if not self._check_image_square(cur_img.size):
                return
            if cur_img.size[1] != images[0].size[1]:  # height not equal
                return
            images.append(cur_img)
        _tmp = 0
        x_coord = [0]
        for i in range(3):
            _tmp += images[i].size[0]
            x_coord.append(_tmp)
        y_coord = [0, first_image.size[1]]

        async def process_row(row: int) -> bool:
            if len(self.pics) < (row + 1) * 3:
                return False
            row_first_img = await self._pic_url_to_image(self.pics[row * 3])
            if not self._check_image_square(row_first_img.size):
                return False
            if row_first_img.size[0] != images[0].size[0]:
                return False
            image_row: list[PILImage.Image] = [row_first_img]
            for i in range(row * 3 + 1, row * 3 + 3):
                cur_img = await self._pic_url_to_image(self.pics[i])
                if not self._check_image_square(cur_img.size):
                    return False
                if cur_img.size[1] != row_first_img.size[1]:
                    return False
                if cur_img.size[0] != images[i % 3].size[0]:
                    return False
                image_row.append(cur_img)
            images.extend(image_row)
            y_coord.append(y_coord[-1] + row_first_img.size[1])
            return True

        if await process_row(1):
            matrix = (3, 2)
        else:
            matrix = (3, 1)
        if await process_row(2):
            matrix = (3, 3)
        logger.info("trigger merge image")
        target = PILImage.new("RGB", (x_coord[-1], y_coord[-1]))
        for y in range(matrix[1]):
            for x in range(matrix[0]):
                target.paste(
                    images[y * matrix[0] + x],
                    (x_coord[x], y_coord[y], x_coord[x + 1], y_coord[y + 1]),
                )
        target_io = BytesIO()
        target.save(target_io, "JPEG")
        self.pics = self.pics[matrix[0] * matrix[1] :]
        self.pics.insert(0, target_io.getvalue())
