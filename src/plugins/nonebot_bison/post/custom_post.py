from dataclasses import dataclass
from pathlib import Path

from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.log import logger
from nonebot.plugin import require

from .abstract_post import AbstractPost, BasePost


@dataclass
class _CustomPost(BasePost):

    message_segments: list[MessageSegment]
    css_path: str = ""  # 模板文件所用css路径

    async def generate_text_messages(self) -> list[MessageSegment]:
        return self.message_segments

    async def generate_pic_messages(self) -> list[MessageSegment]:
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import md_to_pic

        pic_bytes = await md_to_pic(
            md=self._generate_md(), css_path=self._get_css_path()
        )
        return [MessageSegment.image(pic_bytes)]

    def _generate_md(self) -> str:
        md = ""

        for message_segment in self.message_segments:
            if message_segment.type == "text":
                md += "{}\n".format(message_segment.data.get("text", ""))
            elif message_segment.type == "image":
                try:
                    # 先尝试获取file的值，没有在尝试获取url的值，都没有则为空
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

    def _get_css_path(self):
        """返回css路径"""
        css_path = (
            str(Path(__file__).parent / "templates" / "custom_post.css")
            if not self.css_path
            else self.css_path
        )
        return css_path


@dataclass
class CustomPost(_CustomPost, AbstractPost):
    """
    CustomPost所支持的MessageSegment type为text/image

    通过将text/image转换成对应的markdown语法, 生成markdown文本

    最后使用htmlrender渲染为图片
    """

    pass
