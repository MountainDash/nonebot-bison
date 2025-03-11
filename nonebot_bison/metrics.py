import time

from nonebot import require

require("nonebot_plugin_prometheus")
from nonebot_plugin_prometheus import Counter, Gauge, Histogram

# Request counter
request_counter = Counter(
    "bison_request_counter", "The number of requests", ["site_name", "platform_name", "target", "success"]
)

# Sent counter
sent_counter = Counter("bison_sent_counter", "The number of sent messages", ["site_name", "platform_name", "target"])

cookie_choose_counter = Counter(
    "bison_cookie_choose_counter", "The number of cookie choose", ["site_name", "target", "cookie_id"]
)

request_time_histogram = Histogram(
    "bison_request_histogram",
    "The time of platform used to request the source",
    ["site_name", "platform_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

render_time_histogram = Histogram(
    "bison_render_histogram",
    "The time of theme used to render",
    ["site_name", "platform_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
)

start_time = Gauge("bison_start_time", "The start time of the program")
start_time.set(time.time())
