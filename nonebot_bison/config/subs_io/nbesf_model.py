""" nbexf is Nonebot Bison Enchangable Subscribes File! """

from pydantic import BaseModel

from ...types import Category, Tag

# ===== nbesf 定义格式 ====== #
NBESF_VERSION = 1


class UserHead(BaseModel, orm_mode=True):
    """Bison快递包收货信息"""

    type: str
    uid: int

    def __hash__(self):
        return hash((self.type, self.uid))


class Target(BaseModel, orm_mode=True):
    """Bsion快递包发货信息"""

    target_name: str
    target: str
    platform_name: str
    default_schedule_weight: int


class SubPayload(BaseModel, orm_mode=True):
    """Bison快递包里的单件货物"""

    categories: list[Category]
    tags: list[Tag]
    target: Target


class SubPack(BaseModel):
    """Bison给指定用户派送的快递包"""

    user: UserHead
    subs: list[SubPayload]


class SubGroup(BaseModel):
    """
    Bison的全部订单(按用户分组)

    结构参见`nbesf_model.py`
    """

    version: int = NBESF_VERSION  # 表示nbesf格式版本，从1开始
    groups: list[SubPack]


# ======================= #


class SubReceipt(BaseModel):
    """
    快递包中每件货物的收据

    导入订阅时的Model
    """

    user: int
    user_type: str
    target: str
    target_name: str
    platform_name: str
    cats: list[Category]
    tags: list[Tag]
    # default_schedule_weight: int


class NBESFVerMatchErr(Exception):
    ...


class NBESFParseErr(Exception):
    ...
