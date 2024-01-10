from collections import deque

from nonebot_plugin_saa import MessageFactory, PlatformTarget, AggregatedMessageFactory

from nonebot_bison.post import Post
from nonebot_bison.theme import Parcel

Sendable = MessageFactory | AggregatedMessageFactory

MESSAGE_SEND_QUEUE = deque[tuple[PlatformTarget, Sendable, int]]()
MESSAGE_SEND_INTERVAL = 1.5

RENDER_QUEUE = deque[tuple[PlatformTarget, Post]]()
RENDER_INTERVAL = 0

DELIVERY_QUEUE = deque[Parcel]()
DELIVERY_INTERVAL = 0
