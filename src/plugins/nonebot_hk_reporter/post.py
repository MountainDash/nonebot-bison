import base64
from dataclasses import dataclass, field
from io import BytesIO
from typing import NoReturn, Optional
from nonebot import logger
import httpx
from PIL import Image
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

    async def _pic_merge(self) -> None:
        if len(self.pics) < 6:
            return
        first_image = await self._pic_url_to_image(self.pics[0])
        if first_image.size[0] != first_image.size[1]:
            return
        pic_size = first_image.size[0]
        images = [first_image]
        for pic in self.pics[1:]:
            cur_image = await self._pic_url_to_image(pic)
            if cur_image.size[0] != pic_size or cur_image.size[1] != pic_size:
                break
            images.append(cur_image)
        if len(images) == 6:
            matrix = (3, 2)
            self.pics = self.pics[6:]
        elif len(images) >= 9:
            matrix = (3, 3)
            self.pics = self.pics[9:]
        else:
            return
        logger.info('trigger merge image')
        target = Image.new('RGB', (matrix[0] * pic_size, matrix[1] * pic_size))
        for y in range(matrix[1]):
            for x in range(matrix[0]):
                target.paste(images[y * matrix[0] + x], (
                    x * pic_size, y * pic_size, (x + 1) * pic_size, (y + 1) * pic_size
                    ))
        target_io = BytesIO()
        target.save(target_io, 'JPEG')
        b64image = 'base64://' + base64.b64encode(target_io.getvalue()).decode()
        self.pics.insert(0, b64image)

    async def generate_messages(self):
        await self._pic_merge()
        msgs = []
        text = '来源: {}'.format(self.target_type)
        if self.target_name:
            text += ' {}'.format(self.target_name)
        if self.text:
            text += ' \n{}'.format(self.text)
        if self._use_pic():
            msgs.append(await parse_text(text))
            if not self.target_type == 'rss' and self.url:
                msgs.append(self.url)
        else:
            if self.url:
                text += ' \n详情: {}'.format(self.url)
            msgs.append(text)
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
                self.url,
                ', '.join(map(lambda x: 'b64img' if x.startswith('base64') else x, self.pics))
            )
