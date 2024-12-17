import typing

from nonebug.app import App
import pytest

if typing.TYPE_CHECKING:
    import sys

    sys.path.append("./src/plugins")
    from nonebot_bison.config.config_legacy import Config


@pytest.fixture
def config_legacy(app: App, use_legacy_config):
    from nonebot_bison.config import config_legacy as config

    config.start_up()

    yield config.Config()

    config.Config().db.close()


def test_create_and_get(config_legacy: "Config", app: App):
    from nonebot_bison import types
    from nonebot_bison.types import Target

    config_legacy.add_subscribe(
        user=123,
        user_type="group",
        target="weibo_id",
        target_name="weibo_name",
        target_type="weibo",
        cats=[],
        tags=[],
    )
    confs = config_legacy.list_subscribe(123, "group")
    assert len(confs) == 1
    assert config_legacy.target_user_cache["weibo"][Target("weibo_id")] == [types.User(123, "group")]
    assert confs[0]["cats"] == []
    config_legacy.update_subscribe(
        user=123,
        user_type="group",
        target="weibo_id",
        target_name="weibo_name",
        target_type="weibo",
        cats=["1"],
        tags=[],
    )
    confs = config_legacy.list_subscribe(123, "group")
    assert len(confs) == 1
    assert confs[0]["cats"] == ["1"]
