import time

from black.trans import defaultdict
from nonebot import on_command, require
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me

require("nonebot_plugin_prometheus")
from nonebot_plugin_prometheus import Counter, Gauge, Histogram
from prometheus_client import REGISTRY, Metric
from prometheus_client.core import Sample

# Request counter
request_counter = Counter(
    "bison_request_counter", "The number of requests", ["site_name", "platform_name", "target", "success"]
)

# Sent counter
sent_counter = Counter("bison_sent_counter", "The number of sent messages", ["site_name", "platform_name", "target"])

cookie_choose_counter = Counter(
    "bison_cookie_choose_counter", "The number of cookie choose", ["site_name", "target", "cookie_id"]
)

request_histogram = Histogram(
    "bison_request_histogram",
    "The time of platform used to request the source",
    ["site_name", "platform_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

render_histogram = Histogram(
    "bison_render_histogram",
    "The time of theme used to render",
    ["site_name", "platform_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

start_time = Gauge("bison_start_time", "The start time of the program")
start_time.set(time.time())

inspect_scheduler = on_command("inspect-bison", priority=5, rule=to_me(), permission=SUPERUSER)


def sum_counter(counter: Metric) -> int:
    sample_name = counter.name + "_total"
    return int(sum([sample.value for sample in counter.samples if sample.name == sample_name]))


def group_by_label(metric: Metric, label: str):
    mp = defaultdict(list)
    for sample in metric.samples:
        if "_created" in sample.name:
            continue
        mp[sample.labels[label]].append(sample)

    return mp


def generate_dict_from(sample: Sample, key: str) -> str:
    return f"{sample.labels[key]}: {sample.value}"


@inspect_scheduler.handle()
async def inspect_scheduler_handle():
    from nonebot_bison.utils import dict_to_str

    reg = {x.name: x for x in REGISTRY.collect()}
    report = {
        f"Bison 数据统计，截止到 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}": None,
        "调度统计": {
            k: [generate_dict_from(s, "target") for s in v]
            for k, v in group_by_label(reg["bison_request_counter"], "platform_name").items()
        },
        "发送次数": {
            k: [generate_dict_from(s, "target") for s in v]
            for k, v in group_by_label(reg["bison_sent_counter"], "platform_name").items()
        },
        "Cookie 选择次数": {
            k: [generate_dict_from(s, "cookie_id") for s in v]
            for k, v in group_by_label(reg["bison_cookie_choose_counter"], "site_name").items()
        },
    }

    await inspect_scheduler.send("统计数据仅为本次启动后的数据，不包含历史数据")
    await inspect_scheduler.finish(dict_to_str(report))
