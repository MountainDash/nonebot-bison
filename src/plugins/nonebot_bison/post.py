from dataclasses import dataclass, field
from functools import reduce
from io import BytesIO
from typing import Optional, Union

import httpx
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.log import logger
from PIL import Image

from .plugin_config import plugin_config
from .utils import parse_text


@dataclass
class Post:

    target_type: str
    text: str
    url: Optional[str] = None
    target_name: Optional[str] = None
    compress: bool = False
    override_use_pic: Optional[bool] = None
    pics: list[Union[str, bytes]] = field(default_factory=list)
    extra_msg: list[Message] = field(default_factory=list)

    _message: Optional[list[Message]] = None

    def _use_pic(self):
        if not self.override_use_pic is None:
            return self.override_use_pic
        return plugin_config.bison_use_pic

    async def _pic_url_to_image(self, data: Union[str, bytes]) -> Image.Image:
        pic_buffer = BytesIO()
        if isinstance(data, str):
            async with httpx.AsyncClient() as client:
                res = await client.get(data)
            pic_buffer.write(res.content)
        else:
            pic_buffer.write(data)
        return Image.open(pic_buffer)

    def _check_image_square(self, size: tuple[int, int]) -> bool:
        return abs(size[0] - size[1]) / size[0] < 0.05

    async def _pic_merge(self) -> None:
        if len(self.pics) < 3:
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

        if await process_row(1):
            matrix = (3, 2)
        else:
            matrix = (3, 1)
        if await process_row(2):
            matrix = (3, 3)
        logger.info("trigger merge image")
        target = Image.new("RGB", (x_coord[-1], y_coord[-1]))
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

    async def generate_messages(self) -> list[Message]:
        if self._message is None:
            await self._pic_merge()
            msg_segments: list[MessageSegment] = []
            text = ""
            if self.text:
                if self._use_pic():
                    text += "{}".format(self.text)
                else:
                    text += "{}".format(
                        self.text if len(self.text) < 500 else self.text[:500] + "..."
                    )
            text += "\n来源: {}".format(self.target_type)
            if self.target_name:
                text += " {}".format(self.target_name)
            if self._use_pic():
                msg_segments.append(await parse_text(text))
                if not self.target_type == "rss" and self.url:
                    msg_segments.append(MessageSegment.text(self.url))
            else:
                if self.url:
                    text += " \n详情: {}".format(self.url)
                msg_segments.append(MessageSegment.text(text))
            for pic in self.pics:
                msg_segments.append(MessageSegment.image(pic))
            if self.compress:
                msgs = [reduce(lambda x, y: x.append(y), msg_segments, Message())]
            else:
                msgs = list(
                    map(lambda msg_segment: Message([msg_segment]), msg_segments)
                )
            msgs.extend(self.extra_msg)
            self._message = msgs
        assert len(self._message) > 0, f"message list empty, {self}"
        return self._message

    def __str__(self):
        return "type: {}\nfrom: {}\ntext: {}\nurl: {}\npic: {}".format(
            self.target_type,
            self.target_name,
            self.text if len(self.text) < 500 else self.text[:500] + "...",
            self.url,
            ", ".join(
                map(
                    lambda x: "b64img"
                    if isinstance(x, bytes) or x.startswith("base64")
                    else x,
                    self.pics,
                )
            ),
        )
