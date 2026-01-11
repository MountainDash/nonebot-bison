from .platform import FilterMixin


class NewMessageFilter[RawPost](FilterMixin[RawPost]):
    """该平台需要发送订阅目标所发送的新动态消息"""
    # TODO：在 core 外实现

