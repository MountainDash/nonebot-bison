from pydantic import BaseModel, root_validator


class CeoboInfo(BaseModel):
    """卡片的信息部分

    datasource: 数据来源

    time: 时间
    """

    datasource: str
    time: str


class CeoboContent(BaseModel):
    """卡片的内容部分

    image: 图片链接
    text: 文字内容
    """

    image: str | None
    text: str | None

    @root_validator
    def check(cls, values):
        if values["image"] is None and values["text"] is None:
            raise ValueError("image and text cannot be both None")
        return values
    
class CeoboRetweet(BaseModel):
    """卡片的转发部分

    author: 原作者
    image: 图片链接
    content: 文字内容
    """

    image: str | None
    content: str | None
    author: str | None

    @root_validator
    def check(cls, values):
        if values["image"] is None and values["text"] is None:
            raise ValueError("image and text cannot be both None")
        return values


class Card(BaseModel):
    """卡片

    info: 卡片的信息部分
    content: 卡片的内容部分
    qr: 二维码链接
    """

    info: CeoboInfo
    content: CeoboContent
    qr: str
    retweet: CeoboRetweet | None
