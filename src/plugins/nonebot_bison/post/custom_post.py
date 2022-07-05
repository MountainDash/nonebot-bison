from dataclasses import dataclass, field
from pathlib import Path

from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.log import logger
from nonebot.plugin import require

from .abstract_post import AbstractPost, BasePost


@dataclass
class _CustomPost(BasePost):

    message_segments: list[MessageSegment] = field(default_factory=list)
    css_path: str = None  # 模板文件所用css路径

    async def generate_text_messages(self) -> list[MessageSegment]:
        return self.message_segments

    async def generate_pic_messages(self) -> list[MessageSegment]:
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import md_to_pic

        pic_bytes = await md_to_pic(md=self._generate_md(), css_path=self.css_path)
        return [MessageSegment.image(pic_bytes)]

    def _generate_md(self) -> str:
        md = ""

        for message_segment in self.message_segments:
            if message_segment.type == "text":
                md += "{}<br>".format(message_segment.data.get("text", ""))
            elif message_segment.type == "image":
                try:
                    # 先尝试获取file的值，没有再尝试获取url的值，都没有则为空
                    pic_res = message_segment.data.get(
                        "file", message_segment.data.get("url", "")
                    )
                    assert pic_res
                except AssertionError:
                    logger.warning("无法获取到图片资源:MessageSegment.image中file/url字段均为空")
                else:
                    md += "![Image]({})\n".format(pic_res)
            else:
                logger.warning("custom_post不支持处理类型:{}".format(message_segment.type))
                continue

        return md


@dataclass
class CustomPost(_CustomPost, AbstractPost):
    """
    CustomPost所支持的MessageSegment type为text/image

    通过将text/image转换成对应的markdown语法, 生成markdown文本

    理论上text部分可以直接使用markdown语法, 例如 ###123

    注意：list中的每一个text都会被解释为独立的一行文字

    最后使用htmlrender渲染为图片
    """

    pass
