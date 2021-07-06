import base64
from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional

from PIL import Image
import httpx
from nonebot import logger

from .plugin_config import plugin_config
from .utils import parse_text

@dataclass
class Post:

    target_type: str
    text: str
    url: Optional[str]
    target_name: Optional[str] = None
    compress: bool = False
    override_use_pic: Optional[bool] = None

    pics: list[str] = field(default_factory=list)

    def _use_pic(self):
        if not self.override_use_pic is None:
            return self.override_use_pic
        return plugin_config.hk_reporter_use_pic

    async def _pic_url_to_image(self, url: str) -> Image.Image:
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
        pic_buffer = BytesIO()
        pic_buffer.write(res.content)
        return Image.open(pic_buffer)

    def _check_image_square(self, size: tuple[int, int]) -> bool:
        return abs(size[0] - size[1]) / size[0] < 0.01

    async def _pic_merge(self) -> None:
        if len(self.pics) < 6:
            return
        first_image = await self._pic_url_to_image(self.pics[0])
        if not self._check_image_square(first_image.size):
            return
        images: list[Image.Image] = [first_image]
        # first row
        for i in range(1, 3):
            cur_img = await self._pic_url_to_image(self.pics[i])
            if not self._check_image_square(cur_img.size):
                return
            if cur_img.size[1] != images[0].size[1]: # height not equal
                return
            images.append(cur_img)
        _tmp = 0
        x_coord = [0]
        for i in range(3):
            _tmp += images[i].size[0]
            x_coord.append(_tmp)
        y_coord = [0, first_image.size[1]]
        async def process_row(row: int) -> bool:
            row_first_img = await self._pic_url_to_image(self.pics[row * 3])
            if not self._check_image_square(row_first_img.size):
                return False
            if row_first_img.size[0] != images[0].size[0]:
                return False
            image_row: list[Image.Image] = [row_first_img]
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
        if not await process_row(1):
            return
        matrix = (3,2)
        if await process_row(2):
            matrix = (3,3)
        logger.info('trigger merge image')
        target = Image.new('RGB', (x_coord[-1], y_coord[-1]))
        for y in range(matrix[1]):
            for x in range(matrix[0]):
                target.paste(images[y * matrix[0] + x], (
                    x_coord[x], y_coord[y], x_coord[x+1], y_coord[y+1]
                    ))
        target_io = BytesIO()
        target.save(target_io, 'JPEG')
        b64image = 'base64://' + base64.b64encode(target_io.getvalue()).decode()
        self.pics = self.pics[matrix[0] * matrix[1]: ]
        self.pics.insert(0, b64image)

    async def generate_messages(self):
        await self._pic_merge()
        msgs = []
        text = ''
        if self.target_name:
            text += ' {}'.format(self.target_name)
        if self.text:
            text += ' \n{}'.format(self.text if len(self.text) < 500 else self.text[:500] + '...')
        if self._use_pic():
            msgs.append(await parse_text(text))
            if not self.target_type == 'rss' and self.url:
                msgs.append(self.url)
        else:
            if self.url:
                text += ' \n详情: {}'.format(self.url)
            msgs.append(text)
        text += '来源: {}'.format(self.target_type)
        for pic in self.pics:
            msgs.append("[CQ:image,file={url}]".format(url=pic))
        if self.compress:
            msgs = [''.join(msgs)]
        return msgs

    def __str__(self):
        return 'type: {}\nfrom: {}\ntext: {}\nurl: {}\npic: {}'.format(
                self.target_type,
                self.target_name,
                self.text,
                self.text if len(self.text) < 500 else self.text[:500] + '...',
                ', '.join(map(lambda x: 'b64img' if x.startswith('base64') else x, self.pics))
            )
