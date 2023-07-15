from dataclasses import field, dataclass

from nonebot.log import logger
from nonebot.plugin import require
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot_plugin_saa import Text, Image, MessageSegmentFactory

from .abstract_post import BasePost, AbstractPost


@dataclass
class _CustomPost(BasePost):
    ms_factories: list[MessageSegmentFactory] = field(default_factory=list)
    css_path: str | None = None  # 模板文件所用css路径

    async def generate_text_messages(self) -> list[MessageSegmentFactory]:
        return self.ms_factories

    async def generate_pic_messages(self) -> list[MessageSegmentFactory]:
        require("nonebot_plugin_htmlrender")
        from nonebot_plugin_htmlrender import md_to_pic

        pic_bytes = await md_to_pic(md=self._generate_md(), css_path=self.css_path)
        return [Image(pic_bytes)]

    def _generate_md(self) -> str:
        md = ""

        for message_segment in self.ms_factories:
            match message_segment:
                case Text(data={"text": text}):
                    md += f"{text}<br>"
                case Image(data={"image": image}):
                    # use onebot v11 to convert image into url
                    ob11_image = MessageSegment.image(image)
                    md += "![Image]({})\n".format(ob11_image.data["file"])
                case _:
                    logger.warning(f"custom_post不支持处理类型:{type(message_segment)}")
                    continue

        return md


@dataclass
class CustomPost(_CustomPost, AbstractPost):
    """基于 markdown 语法的，自由度较高的推送内容格式

    简介:
    支持处理text/image两种MessageSegmentFactory,
    通过将text/image转换成对应的markdown语法以生成markdown文本。
    理论上text类型中可以直接使用markdown语法,例如`##第一章`。
    但会导致不启用`override_use_pic`时, 发送不会被渲染的纯文本消息。
    图片渲染最终由htmlrender执行。

    注意:
    每一个MessageSegmentFactory元素都会被解释为单独的一行

    可选参数:
    `override_use_pic`:是否覆盖`bison_use_pic`全局配置
    `compress`:将所有消息压缩为一条进行发送
    `extra_msg`:需要附带发送的额外消息

    成员函数:
    `generate_text_messages()`:负责生成文本消息
    `generate_pic_messages()`:负责生成图片消息
    """

    pass
