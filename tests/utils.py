import io
import base64
from typing import TYPE_CHECKING, Literal, TypedDict

from PIL import Image

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent


class AppReq(TypedDict, total=False):
    refresh_bot: bool
    no_init_db: bool


async def show_pic(pic_data: str | bytes):
    """
    用来在测试时查看图片的函数，接受的参数为图片的数据
    # 警告: 请确保在正式运行时不会调用此函数，否则会导致测试卡死

    允许的数据类型：

    `str`: base64编码的字符串，应以base64://开头

    `bytes`: 图片的二进制数据
    """

    if isinstance(pic_data, str) and pic_data.startswith("base64://"):
        img_bytes = base64.b64decode(pic_data[9:])
    elif isinstance(pic_data, bytes):
        img_bytes = pic_data
    else:
        raise ValueError("pic_data应为base64编码的字符串或图片的二进制数据")

    img = Image.open(io.BytesIO(img_bytes))
    img.show()


def fake_group_message_event(**field) -> "GroupMessageEvent":
    from pydantic import create_model
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent

    _Fake = create_model("_Fake", __base__=GroupMessageEvent)

    class FakeEvent(_Fake):
        time: int = 1000000
        self_id: int = 1
        post_type: Literal["message"] = "message"
        sub_type: str = "normal"
        user_id: int = 10
        message_type: Literal["group"] = "group"
        group_id: int = 10000
        message_id: int = 1
        message: Message = Message("test")
        raw_message: str = "test"
        font: int = 0
        sender: Sender = Sender(
            card="",
            nickname="test",
            role="member",
        )
        to_me: bool = False

        class Config:
            extra = "forbid"

    return FakeEvent(**field)


def fake_private_message_event(**field) -> "PrivateMessageEvent":
    from pydantic import create_model
    from nonebot.adapters.onebot.v11.event import Sender
    from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent

    _Fake = create_model("_Fake", __base__=PrivateMessageEvent)

    class FakeEvent(_Fake):
        time: int = 1000000
        self_id: int = 1
        post_type: Literal["message"] = "message"
        sub_type: str = "friend"
        user_id: int = 10
        message_type: Literal["private"] = "private"
        message_id: int = 1
        message: Message = Message("test")
        raw_message: str = "test"
        font: int = 0
        sender: Sender = Sender(nickname="test")
        to_me: bool = False

        class Config:
            extra = "forbid"

    return FakeEvent(**field)


from nonebot.adapters.onebot.v11.event import Sender

fake_admin_user = Sender(nickname="test", role="admin")
fake_superuser = Sender(user_id=10001, nickname="superuser")

add_reply_on_id_input_search = (
    "https://nonebot-bison.netlify.app/usage/#%E6%89%80%E6%94%AF%E6%8C%81%E5%B9%B3%E5%8F%B0%E7%9A%84-uid"
)


class BotReply:
    @staticmethod
    def add_reply_on_platform(platform_manager, common_platform):
        return (
            "请输入想要订阅的平台，目前支持，请输入冒号左边的名称：\n"
            + "".join(
                [f"{platform_name}: {platform_manager[platform_name].name}\n" for platform_name in common_platform]
            )
            + "要查看全部平台请输入：“全部”\n中止订阅过程请输入：“取消”"
        )

    @staticmethod
    def add_reply_on_platform_input_allplatform(platform_manager):
        return "全部平台\n" + "\n".join(
            [f"{platform_name}: {platform.name}" for platform_name, platform in platform_manager.items()]
        )

    @staticmethod
    def add_reply_on_id_input_search_ob11():
        from nonebot.adapters.onebot.v11 import MessageSegment

        search_title = "Bison所支持的平台UID"
        search_content = "查询相关平台的uid格式或获取方式"
        search_image = "https://s3.bmp.ovh/imgs/2022/03/ab3cc45d83bd3dd3.jpg"

        return MessageSegment.share(
            url=add_reply_on_id_input_search,
            title=search_title,
            content=search_content,
            image=search_image,
        )

    @staticmethod
    def add_reply_on_target_confirm(platform, name, id):
        return f"即将订阅的用户为:{platform} {name} {id}\n如有错误请输入“取消”重新订阅"

    @staticmethod
    def add_reply_on_cats(platform_manager, platform: str):
        return (
            "请输入要订阅的类别，以空格分隔，"
            f"支持的类别有：{' '.join(list(platform_manager[platform].categories.values()))}"
        )

    @staticmethod
    def add_reply_on_cats_input_error(cat: str):
        return f"不支持 {cat}"

    @staticmethod
    def add_reply_subscribe_success(name):
        return f"添加 {name} 成功"

    @staticmethod
    def add_reply_on_id(platform: object) -> str:
        target_promot: str = platform.parse_target_promot  # type: ignore
        base_text = "请输入订阅用户的id\n查询id获取方法请回复:“查询”"
        extra_text = ("1." + target_promot + "\n2.") if target_promot else ""
        return extra_text + base_text

    add_reply_on_id_input_error = "id输入错误"
    add_reply_on_target_parse_input_error = "不能从你的输入中提取出id，请检查你输入的内容是否符合预期"
    add_reply_on_platform_input_error = "平台输入错误"
    add_reply_on_tags = (
        '请输入要订阅/屏蔽的标签(不含#号)\n多个标签请使用空格隔开\n订阅所有标签输入"全部标签"\n具体规则回复"详情"'
    )
    add_reply_on_tags_need_more_info = "订阅标签直接输入标签内容\n屏蔽标签请在标签名称前添加~号\n详见https://nonebot-bison.netlify.app/usage/#%E5%B9%B3%E5%8F%B0%E8%AE%A2%E9%98%85%E6%A0%87%E7%AD%BE-tag"
    add_reply_abort = "已中止订阅"
