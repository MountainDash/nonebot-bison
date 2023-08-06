from pydantic import BaseModel

HTML = str


class Card(BaseModel):
    """Arknight 公告卡片

    announce_title: 公告标题
    banner_image_url: 横幅图片 URL
    content: 公告内容, 应为 HTML 文本
    """

    announce_title: str
    banner_image_url: str | None
    content: HTML
