from pathlib import Path
from shutil import rmtree
import sys

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter
from nonebug import NONEBOT_INIT_KWARGS, App
import pytest
from pytest_mock.plugin import MockerFixture
from sqlalchemy import delete

from .utils import AppReq


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "datastore_database_url": "sqlite+aiosqlite:///:memory:",
        "superusers": {"10001"},
        "command_start": {""},
        "log_level": "TRACE",
        "bison_use_browser": True,
    }


@pytest.fixture(scope="session", autouse=True)
def load_adapters(nonebug_init: None):
    driver = nonebot.get_driver()
    driver.register_adapter(OnebotV11Adapter)
    return driver


def patch_refresh_bilibili_anonymous_cookie(mocker: MockerFixture):
    # patch 掉bilibili的匿名cookie生成函数，避免真实请求

    from nonebot_bison.platform.bilibili.scheduler import BilibiliClientManager

    mocker.patch.object(
        BilibiliClientManager, "_get_cookies", return_value=[{"name": "test anonymous", "content": "test"}]
    )


@pytest.fixture
async def app(tmp_path: Path, request: pytest.FixtureRequest, mocker: MockerFixture):
    sys.path.append(str(Path(__file__).parent.parent / "src" / "plugins"))

    nonebot.require("nonebot_bison")
    from nonebot_plugin_datastore.config import plugin_config as datastore_config
    from nonebot_plugin_datastore.db import create_session, init_db
    from nonebot_plugin_htmlrender.browser import shutdown_browser

    from nonebot_bison import plugin_config
    from nonebot_bison.config.db_model import ScheduleTimeWeight, Subscribe, Target, User

    plugin_config.bison_config_path = str(tmp_path / "legacy_config")
    plugin_config.bison_filter_log = False
    plugin_config.bison_use_browser = True

    datastore_config.datastore_config_dir = tmp_path / "config"
    datastore_config.datastore_cache_dir = tmp_path / "cache"
    datastore_config.datastore_data_dir = tmp_path / "data"

    param: AppReq = getattr(request, "param", AppReq())

    # 如果在 app 前调用会报错“无法找到调用者”
    # 而在后面调用又来不及mock，所以只能在中间mock
    patch_refresh_bilibili_anonymous_cookie(mocker)

    if not param.get("no_init_db"):
        await init_db()
    # if not param.get("refresh_bot"):
    #     import nonebot_bison.utils.get_bot
    #
    #     mocker.patch.object(nonebot_bison.utils.get_bot, "refresh_bots")

    yield App()

    # cleanup
    async with create_session() as session, session.begin():
        await session.execute(delete(User))
        await session.execute(delete(Subscribe))
        await session.execute(delete(Target))
        await session.execute(delete(ScheduleTimeWeight))

    # 关闭渲染图片时打开的浏览器
    await shutdown_browser()
    # 清除缓存文件
    cache_dir = Path.cwd() / ".cache" / "hishel"
    if cache_dir.exists():
        rmtree(cache_dir)
        cache_dir.mkdir()


@pytest.fixture
def dummy_user_subinfo(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_bison.types import UserSubInfo

    user = TargetQQGroup(group_id=123)
    return UserSubInfo(user=user, categories=[], tags=[])


@pytest.fixture
async def init_scheduler(app: App):
    from nonebot_bison.scheduler.manager import init_scheduler

    return await init_scheduler()


@pytest.fixture
async def use_legacy_config(app: App):
    import aiofiles

    from nonebot_bison.config.config_legacy import Config, get_config_path
    from nonebot_bison.utils import Singleton

    # 默认不创建配置所在的文件夹
    # 如果需要测试需要手动创建相关文件夹
    path = Path(get_config_path()[0])
    path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(path, "w") as f:
        await f.write("{}")

    Config()._do_init()

    yield None

    # 清除单例的缓存
    Singleton._instances.clear()


@pytest.fixture
async def _no_browser(app: App, mocker: MockerFixture):
    from nonebot_bison.platform import _get_unavailable_platforms
    from nonebot_bison.plugin_config import plugin_config

    mocker.patch.object(plugin_config, "bison_use_browser", False)
    mocker.patch("nonebot_bison.platform.unavailable_paltforms", _get_unavailable_platforms())


@pytest.fixture
async def _clear_db(app: App):
    from nonebot_bison.config import config

    await config.clear_db()
    yield
    await config.clear_db()
    return


@pytest.fixture
def _patch_weibo_get_cookie_name(app: App, mocker: MockerFixture):
    from nonebot_bison.platform import weibo

    mocker.patch.object(weibo.WeiboClientManager, "_get_current_user_name", return_value="test_name")
    yield
    mocker.stopall()
