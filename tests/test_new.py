import pytest


def test_add(n_plugin_module):
    from nonebot_bison.config import Config

    config = Config()
    config.add_subscribe(
        user="123",
        user_type="group",
        target="weibo_id",
        target_name="weibo_name",
        target_type="weibo",
        cats=[],
        tags=[],
    )
