from typing import Any

from httpx import AsyncClient
from pydantic import BaseModel, parse_obj_as

from nonebot_bison.types import Target

from ..post import Post
from ..types import Target
from ..utils import scheduler
from .platform import NewMessage
from ..card.themes import PlainStem


class FF14Post(BaseModel):
    Id: int
    ApplicationCode: int
    Articletype: int
    Author: str
    CategoryCode: int
    GroupIndex: int
    HomeImagePath: str
    OutLink: str
    PublishDate: str
    SortIndex: int
    Summary: str
    Title: str
    TitleClass: str


class FF14(NewMessage[FF14Post]):
    categories = {}
    platform_name = "ff14"
    name = "最终幻想XIV官方公告"
    enable_tag = False
    enabled = True
    is_common = False
    scheduler_class = "ff14"
    scheduler = scheduler("interval", {"seconds": 60})
    has_target = False

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        return "最终幻想XIV官方公告"

    async def get_sub_list(self, _) -> list[FF14Post]:
        raw_data = await self.client.get(
            "https://cqnews.web.sdo.com/api/news/newsList?gameCode=ff&CategoryCode=5309,5310,5311,5312,5313&pageIndex=0&pageSize=5"
        )
        return parse_obj_as(list[FF14Post], raw_data.json()["Data"])

    def get_id(self, post: FF14Post) -> Any:
        """用发布时间当作 ID

        因为有时候官方会直接编辑以前的文章内容
        """
        return post.PublishDate

    def get_date(self, _: FF14Post) -> None:
        return None
