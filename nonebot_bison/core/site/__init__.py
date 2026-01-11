from .context import ProcessContext as ProcessContext
from .site import ClientManager as ClientManager
from .site import SiteConfig as SiteConfig


class SkipRequestException(Exception):
    """跳过请求异常，如果需要在选择 Cookie 时跳过此次请求，可以抛出此异常"""

    pass


class CookieFormatException(ValueError):
    """cookie格式错误"""

    pass
