from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.log import logger
from nonebot.plugin import require

from .abstract_post import AbstractPost, BasePost


@dataclass
class _CustomPost(BasePost):

    message_segments: list[MessageSegment] = field(default_factory=list)
    css_path: Optional[str] = None  # 模板文件所用css路径

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
                # 先尝试获取file的值，没有再尝试获取url的值，都没有则为空
                pic_res = message_segment.data.get("file") or message_segment.data.get(
                    "url", ""
                )
                if not pic_res:
                    logger.warning("无法获取到图片资源:MessageSegment.image中file/url字段均为空")
                else:
                    md += "![Image]({})\n".format(pic_res)
            else:
                logger.warning("custom_post不支持处理类型:{}".format(message_segment.type))
                continue

        return md


@dataclass
class CustomPost(_CustomPost, AbstractPost):
    """基于 markdown 语法的，自由度较高的推送内容格式

    简介:
    支持处理text/image两种MessageSegment,
    通过将text/image转换成对应的markdown语法以生成markdown文本。
    理论上text类型中可以直接使用markdown语法,例如`##第一章`。
    但会导致不启用`override_use_pic`时, 发送不会被渲染的纯文本消息。
    图片渲染最终由htmlrender执行。

    注意:
    每一个MessageSegment元素都会被解释为单独的一行

    可选参数:
    `override_use_pic`:是否覆盖`bison_use_pic`全局配置
    `compress`:将所有消息压缩为一条进行发送
    `extra_msg`:需要附带发送的额外消息

    成员函数:
    `generate_text_messages()`:负责生成文本消息
    `generate_pic_messages()`:负责生成图片消息
    """

    pass
