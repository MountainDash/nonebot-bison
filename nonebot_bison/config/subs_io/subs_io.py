from functools import partial
from typing import Any, Callable, Coroutine, Sequence

from nonebot.log import logger

from ..db_config import SubscribeDupException
from ..db_model import Subscribe
from .nbesf_model import (
    NBESFParseErr,
    SubGroup,
    SubPack,
    SubPayload,
    SubReceipt,
    UserHead,
    nbesf_version_checker,
)


async def subscribes_export(
    fetcher_func: Callable[..., Coroutine[Any, Any, Sequence[Subscribe]]]
) -> SubGroup:
    """
    将Bison订阅导出为 Nonebot Bison Exchangable Subscribes File 标准格式的 SubGroup 类型数据
    fetcher_func:
        获取数据库中订阅信息的函数，应返回 db_model 中 Subscribe 类型的list
    """

    db_data_seq = await fetcher_func()

    user_set: set[UserHead] = set()
    groups: list[SubPack] = []
    for item in db_data_seq:

        checking_user = UserHead.from_orm(item.user)
        new_sub_payload = SubPayload.from_orm(item)

        if checking_user in user_set:
            # 已有收货信息？向包裹追加货物！
            for existing_sub_pack in groups:
                if checking_user == existing_sub_pack.user:
                    existing_sub_pack.subs.append(new_sub_payload)
                    break
        else:
            # 新的收货信息？创建新的包裹！
            user_set.add(checking_user)
            new_sub_pack = SubPack(user=checking_user, subs=[new_sub_payload])
            groups.append(new_sub_pack)

    sub_group = SubGroup(groups=groups)

    return sub_group


async def subscribes_import(
    nbesf_data: SubGroup, dumpee_func: Callable[..., Coroutine[Any, Any, Any]]
):
    """
    从 Nonebot Bison Exchangable Subscribes File 标准格式的数据中导入订阅

    nbesf_data:
        符合nbesf_model标准的 SubGroup 类型数据

    dumpee_func:
        向数据库中添加订阅信息的函数
    """

    nbesf_version_checker(nbesf_data.version)

    logger.info("开始添加订阅流程")
    for item in nbesf_data.groups:
        sub_receipt = partial(SubReceipt, user=item.user.uid, user_type=item.user.type)

        for sub in item.subs:
            receipt = sub_receipt(
                target=sub.target.target,
                target_name=sub.target.target_name,
                platform_name=sub.target.platform_name,
                cats=sub.categories,
                tags=sub.tags,
            )
            try:
                await dumpee_func(**receipt.dict())
            except SubscribeDupException:
                logger.warning(f"！添加订阅条目 {repr(receipt)} 失败: 相同的订阅已存在")
            except Exception as e:
                logger.error(f"！添加订阅条目 {repr(receipt)} 失败: {repr(e)}")
            else:
                logger.success(f"添加订阅条目 {repr(receipt)} 成功！")

    logger.info("订阅流程结束，请检查所有订阅记录是否全部添加成功")


def nbesf_parser(raw_data: Any) -> SubGroup:
    try:
        nbesf_data = SubGroup.parse_obj(raw_data)
    except:
        logger.error("该数据格式不满足NBESF格式标准！")
        raise NBESFParseErr
    else:
        return nbesf_data
