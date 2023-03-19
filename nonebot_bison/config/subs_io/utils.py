from functools import partial

from nonebot.log import logger

from ..db_config import SubscribeDupException, config
from .nbesf_model import NBESF_VERSION, SubGroup, SubReceipt


async def subs_receipt_gen_ver_1(nbesf_data: SubGroup):
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
                await config.add_subscribe(**receipt.dict())
            except SubscribeDupException:
                logger.warning(f"！添加订阅条目 {repr(receipt)} 失败: 相同的订阅已存在")
            except Exception as e:
                logger.error(f"！添加订阅条目 {repr(receipt)} 失败: {repr(e)}")
            else:
                logger.success(f"添加订阅条目 {repr(receipt)} 成功！")
