from typing import Any, Literal, TypeVar, TypeAlias

from pydantic import BaseModel
from nonebot.compat import PYDANTIC_V2, ConfigDict

from nonebot_bison.compat import model_rebuild

TBaseModel = TypeVar("TBaseModel", bound=type[BaseModel])


# 不能当成装饰器用
# 当装饰器用时，global namespace 中还没有被装饰的类，会报错
def model_rebuild_recurse(cls: TBaseModel) -> TBaseModel:
    """Recursively rebuild all BaseModel subclasses in the class."""
    if not PYDANTIC_V2:
        from inspect import isclass, getmembers

        for _, sub_cls in getmembers(cls, lambda x: isclass(x) and issubclass(x, BaseModel)):
            model_rebuild_recurse(sub_cls)
    model_rebuild(cls)
    return cls


class Base(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:

        class Config:
            orm_mode = True


class APIBase(Base):
    """Bilibili API返回的基础数据"""

    code: int
    message: str


class UserAPI(APIBase):
    class Card(Base):
        name: str

    class Data(Base):
        card: "UserAPI.Card"

    data: Data | None = None


DynamicType = Literal[
    "DYNAMIC_TYPE_ARTICLE",
    "DYNAMIC_TYPE_AV",
    "DYNAMIC_TYPE_WORD",
    "DYNAMIC_TYPE_DRAW",
    "DYNAMIC_TYPE_FORWARD",
    "DYNAMIC_TYPE_LIVE",
    "DYNAMIC_TYPE_LIVE_RCMD",
    "DYNAMIC_TYPE_PGC",
    "DYNAMIC_TYPE_PGC_UNION",
    "DYNAMIC_TYPE_NONE",  # 已删除的动态，一般只会出现在转发动态的源动态被删除
    "DYNAMIC_TYPE_COMMON_SQUARE",
    "DYNAMIC_TYPE_COMMON_VERTICAL",
    "DYNAMIC_TYPE_COURSES_SEASON",
]


# 参考 https://github.com/Yun-Shan/bilibili-dynamic
class PostAPI(APIBase):
    class Basic(Base):
        rid_str: str
        """可能含义是referrer id，表示引用的对象的ID？
        已知专栏动态时该ID与专栏ID一致，视频动态时与av号一致
        """

    class Modules(Base):
        class Author(Base):
            face: str
            mid: int
            name: str
            jump_url: str
            pub_ts: int
            type: Literal["AUTHOR_TYPE_NORMAL", "AUTHOR_TYPE_PGC"]
            """作者类型，一般情况下都是NORMAL，番剧推送是PGC"""

        class Additional(Base):
            type: str
            """用户发视频时同步发布的动态带图片: ADDITIONAL_TYPE_UGC
            显示相关游戏: ADDITIONAL_TYPE_COMMON
            显示预约: ADDITIONAL_TYPE_RESERVE
            显示投票: ADDITIONAL_TYPE_VOTE
            显示包月充电专属抽奖: ADDITIONAL_TYPE_UPOWER_LOTTERY
            显示赛事时(暂时只看到回放的，理论上直播时应该也是这个): ADDITIONAL_TYPE_MATCH
            """

        class Desc(Base):
            rich_text_nodes: list[dict[str, Any]]
            """描述的富文本节点，组成动态的各种内容"""
            text: str
            """描述的纯文本内容"""

        class Dynamic(Base):
            additional: "PostAPI.Modules.Additional | None" = None
            desc: "PostAPI.Modules.Desc | None" = None
            """动态描述，可能为空"""
            major: "Major | None" = None
            """主要内容，可能为空"""

        module_author: "PostAPI.Modules.Author"
        module_dynamic: "PostAPI.Modules.Dynamic"

    class Topic(Base):
        id: int
        name: str
        jump_url: str

    class Item(Base):
        basic: "PostAPI.Basic"
        id_str: str
        modules: "PostAPI.Modules"
        orig: "PostAPI.Item | None" = None
        topic: "PostAPI.Topic | None" = None
        type: DynamicType

    class DeletedItem(Base):
        basic: "PostAPI.Basic"
        id_str: None
        modules: "PostAPI.Modules"
        type: Literal["DYNAMIC_TYPE_NONE"]

    class Data(Base):
        items: "list[PostAPI.Item | PostAPI.DeletedItem] | None" = None

    data: "PostAPI.Data | None" = None


class VideoMajor(Base):
    class Archive(Base):
        aid: str
        bvid: str
        title: str
        desc: str
        """视频简介，太长的话会被截断"""
        cover: str
        jump_url: str

    type: Literal["MAJOR_TYPE_ARCHIVE"]
    archive: "VideoMajor.Archive"


class LiveRecommendMajor(Base):
    class LiveRecommand(Base):
        content: str
        """直播卡片的内容，值为JSON文本"""

    type: Literal["MAJOR_TYPE_LIVE_RCMD"]
    live_rcmd: "LiveRecommendMajor.LiveRecommand"


class LiveMajor(Base):
    class Live(Base):
        id: int
        """直播间号"""
        title: str
        live_state: int
        """直播状态，1为直播中，0为未开播"""
        cover: str
        desc_first: str
        """直播信息的第一部分，用来显示分区"""
        desc_second: str
        """跳转链接，目前用的是相对协议(即//开头而不是https://开头)"""
        jump_url: str

    type: Literal["MAJOR_TYPE_LIVE"]
    live: "LiveMajor.Live"


class ArticleMajor(Base):
    class Article(Base):
        id: int
        """专栏CID"""
        title: str
        desc: str
        """专栏简介"""
        covers: list[str]
        """专栏封面，一般是一张图片"""
        jump_url: str

    type: Literal["MAJOR_TYPE_ARTICLE"]
    article: "ArticleMajor.Article"


class DrawMajor(Base):
    class Item(Base):
        width: int
        height: int
        size: float
        """文件大小，KiB（1024）"""
        src: str
        """图片链接"""

    class Draw(Base):
        id: int
        items: "list[DrawMajor.Item]"

    type: Literal["MAJOR_TYPE_DRAW"]
    draw: "DrawMajor.Draw"


class PGCMajor(Base):
    """番剧推送"""

    class PGC(Base):
        title: str
        cover: str
        jump_url: str
        """通常https://www.bilibili.com/bangumi/play/ep{epid}"""
        epid: int
        season_id: int

    type: Literal["MAJOR_TYPE_PGC"]
    pgc: "PGCMajor.PGC"


class OPUSMajor(Base):
    """通用图文内容"""

    class Summary(Base):
        rich_text_nodes: list[dict[str, Any]]
        """描述的富文本节点，组成动态的各种内容"""
        text: str

    class Pic(Base):
        width: int
        height: int
        size: int
        """文件大小，KiB（1024）"""
        url: str
        """图片链接"""

    class Opus(Base):
        jump_url: str
        title: str
        summary: "OPUSMajor.Summary"
        pics: "list[OPUSMajor.Pic]"

    type: Literal["MAJOR_TYPE_OPUS"]
    opus: "OPUSMajor.Opus"


class CommonMajor(Base):
    """还是通用图文内容
    主要跟特殊官方功能有关系，例如专属活动页、会员购、漫画、赛事中心、游戏中心、小黑屋、工房集市、装扮等
    """

    class Common(Base):
        cover: str
        """卡片左侧图片的URL"""
        title: str
        desc: str
        """内容"""
        jump_url: str

    type: Literal["MAJOR_TYPE_COMMON"]
    common: "CommonMajor.Common"


class CoursesMajor(Base):
    """课程推送"""

    class Courses(Base):
        title: str
        sub_title: str
        """副标题，一般是课程的简介"""
        desc: str
        """课时信息"""
        cover: str
        jump_url: str
        id: int
        """课程ID"""

    type: Literal["MAJOR_TYPE_COURSES"]
    courses: "CoursesMajor.Courses"


class DeletedMajor(Base):
    class None_(Base):
        tips: str

    type: Literal["MAJOR_TYPE_NONE"]
    none: "DeletedMajor.None_"


class UnknownMajor(Base):
    type: str


Major = (
    VideoMajor
    | LiveRecommendMajor
    | LiveMajor
    | ArticleMajor
    | DrawMajor
    | PGCMajor
    | OPUSMajor
    | CommonMajor
    | CoursesMajor
    | DeletedMajor
    | UnknownMajor
)

DynRawPost: TypeAlias = PostAPI.Item

model_rebuild_recurse(VideoMajor)
model_rebuild_recurse(LiveRecommendMajor)
model_rebuild_recurse(LiveMajor)
model_rebuild_recurse(ArticleMajor)
model_rebuild_recurse(DrawMajor)
model_rebuild_recurse(PGCMajor)
model_rebuild_recurse(OPUSMajor)
model_rebuild_recurse(CommonMajor)
model_rebuild_recurse(CoursesMajor)
model_rebuild_recurse(UserAPI)
model_rebuild_recurse(PostAPI)
