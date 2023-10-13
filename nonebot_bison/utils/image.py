from io import BytesIO
from typing import TypeGuard
from functools import partial

from PIL import Image
from httpx import AsyncClient
from nonebot import logger, require
from PIL.Image import Image as PILImage
from nonebot_plugin_saa import Text as SaaText
from nonebot_plugin_saa import Image as SaaImage

from ..plugin_config import plugin_config


async def pic_url_to_image(data: str | bytes, http_client: AsyncClient) -> PILImage:
    pic_buffer = BytesIO()
    if isinstance(data, str):
        res = await http_client.get(data)
        pic_buffer.write(res.content)
    else:
        pic_buffer.write(data)
    return Image.open(pic_buffer)


def _check_image_square(size: tuple[int, int]) -> bool:
    return abs(size[0] - size[1]) / size[0] < 0.05


async def pic_merge(pics: list[str | bytes], http_client: AsyncClient) -> list[str | bytes]:
    if len(pics) < 3:
        return pics

    _pic_url_to_image = partial(pic_url_to_image, http_client=http_client)

    first_image = await _pic_url_to_image(pics[0])
    if not _check_image_square(first_image.size):
        return pics
    images: list[PILImage] = [first_image]
    # first row
    for i in range(1, 3):
        cur_img = await _pic_url_to_image(pics[i])
        if not _check_image_square(cur_img.size):
            return pics
        if cur_img.size[1] != images[0].size[1]:  # height not equal
            return pics
        images.append(cur_img)
    _tmp = 0
    x_coord = [0]
    for i in range(3):
        _tmp += images[i].size[0]
        x_coord.append(_tmp)
    y_coord = [0, first_image.size[1]]

    async def process_row(row: int) -> bool:
        if len(pics) < (row + 1) * 3:
            return False
        row_first_img = await _pic_url_to_image(pics[row * 3])
        if not _check_image_square(row_first_img.size):
            return False
        if row_first_img.size[0] != images[0].size[0]:
            return False
        image_row: list[PILImage] = [row_first_img]
        for i in range(row * 3 + 1, row * 3 + 3):
            cur_img = await _pic_url_to_image(pics[i])
            if not _check_image_square(cur_img.size):
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
    pics = pics[matrix[0] * matrix[1] :]
    pics.insert(0, target_io.getvalue())

    return pics


def is_pics_mergable(imgs: list) -> TypeGuard[list[str | bytes]]:
    return all(isinstance(img, str | bytes) for img in imgs)


async def text_to_image(saa_text: SaaText) -> SaaImage:
    """使用 htmlrender 将 saa.Text 渲染为 saa.Image"""
    if not plugin_config.bison_use_pic:
        raise ValueError("请启用 bison_use_pic")
    require("nonebot_plugin_htmlrender")
    from nonebot_plugin_htmlrender import text_to_pic

    render_data = await text_to_pic(str(saa_text))
    return SaaImage(render_data)
