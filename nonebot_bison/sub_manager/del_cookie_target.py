from nonebot.matcher import Matcher

from .utils import ensure_user_info, gen_handle_cancel


def do_del_cookie_target(del_cookie_target: type[Matcher]):
    handle_cancel = gen_handle_cancel(del_cookie_target, "删除中止")

    del_cookie_target.handle()(ensure_user_info(del_cookie_target))
