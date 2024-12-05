from functools import wraps
from datetime import datetime
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, Literal, TypeVar, TypedDict

from nonebot_bison.utils import dict_to_str

from ..utils import Site
from ..types import Target

if TYPE_CHECKING:
    from .scheduler import Scheduler, Schedulable


TSchd = TypeVar("TSchd", bound="Scheduler")


RecordKind = Literal["insert_new", "delete"]


class PlatformTargetRecord(TypedDict):
    schedule_count: defaultdict[str, defaultdict[str, int]]
    insert_new: list[tuple[str, datetime]]
    delete: list[tuple[str, datetime]]
    post_send: defaultdict[str, int]


class RuntimeStatistic:
    def __init__(self):
        self._record = PlatformTargetRecord(
            schedule_count=defaultdict(lambda: defaultdict(int)), insert_new=[], delete=[], post_send=defaultdict(int)
        )

    def statistic_schedule_count(self, func: "Callable[[TSchd], Coroutine[Any, Any, Schedulable | None]]"):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not (schedulable := await func(*args, **kwargs)):
                return
            self._record["schedule_count"][schedulable.platform_name][schedulable.target] += 1
            return schedulable

        return wrapper

    def statistic_record(self, name: RecordKind):
        record = self._record[name]

        def decorator(func: "Callable[[TSchd, str, Target], None]"):
            @wraps(func)
            def wrapper(*args, **kwargs):
                platform_name, target = args[1], args[2]
                record.append((f"{platform_name}-{target}", datetime.now()))
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def statistic_post_send(self, platform_name: str):
        self._record["post_send"][platform_name] += 1

    def _generate_stats(self, scheduler_dict: "dict[type[Site], Scheduler]"):
        report_dict: dict[str, Any] = {
            "新增订阅hook调用记录": [f"{record[0]}: {record[1]}" for record in self._record["insert_new"]],
            "删除订阅hook调用记录": [f"{record[0]}: {record[1]}" for record in self._record["delete"]],
        }

        platform_dict = {}
        for platform, targets in self._record["schedule_count"].items():
            target_dict = [f"{target}: {count} 次" for target, count in targets.items()]
            platform_dict[platform] = target_dict
        report_dict["调度统计"] = platform_dict

        post_send_dict = {}
        for platform, count in self._record["post_send"].items():
            post_send_dict[platform] = f"{count} 次"

        report_dict["发送消息统计"] = post_send_dict

        all_schedulable = {}
        for site, scheduler in scheduler_dict.items():
            scheduler_list = []
            for schedulable in scheduler.schedulable_list:
                scheduler_list.append(
                    f"{schedulable.target}: [权重]{schedulable.current_weight} | [批量]{schedulable.use_batch}"
                )
            all_schedulable[site.name] = scheduler_list

        report_dict["所有调度对象"] = all_schedulable

        return report_dict

    def generate_report(self, scheduler_dict: "dict[type[Site], Scheduler]"):
        """根据 schduler_dict 生成报告"""
        report_dict = self._generate_stats(scheduler_dict)
        return dict_to_str(report_dict)


runtime_statistic = RuntimeStatistic()
