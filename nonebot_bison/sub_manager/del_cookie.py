from nonebot.matcher import Matcher

from .utils import ensure_user_info, gen_handle_cancel


def do_del_cookie(del_cookie: type[Matcher]):
    handle_cancel = gen_handle_cancel(del_cookie, "删除中止")

    del_cookie.handle()(ensure_user_info(del_cookie))
