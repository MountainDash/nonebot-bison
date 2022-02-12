import typing

from nonebug.app import App
import pytest

if typing.TYPE_CHECKING:
    import sys

    sys.path.append("./src/plugins")
    import nonebot_bison
    from nonebot_bison.config import Config


@pytest.fixture
def config(app: App):
    from nonebot_bison import config

    config.start_up()
    return config.Config()


def test_create_and_get(config: "Config", app: App):
    from nonebot_bison import types
    from nonebot_bison.types import Target

    config.add_subscribe(
        user="123",
        user_type="group",
        target="weibo_id",
        target_name="weibo_name",
        target_type="weibo",
        cats=[],
        tags=[],
    )
    confs = config.list_subscribe("123", "group")
    assert len(confs) == 1
    assert config.target_user_cache["weibo"][Target("weibo_id")] == [
        types.User("123", "group")
    ]
    assert confs[0]["cats"] == []
    config.update_subscribe(
        user="123",
        user_type="group",
        target="weibo_id",
        target_name="weibo_name",
        target_type="weibo",
        cats=["1"],
        tags=[],
    )
    confs = config.list_subscribe("123", "group")
    assert len(confs) == 1
    assert confs[0]["cats"] == ["1"]
