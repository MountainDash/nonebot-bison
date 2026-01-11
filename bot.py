from pathlib import Path

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.log import logger
from sqlalchemy import StaticPool

nonebot.init(sqlalchemy_engine_options={"poolclass": StaticPool})
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 加载插件
nonebot.load_from_toml("pyproject.toml")
nonebot.load_plugin(Path(__file__) / "for_test_plugin.py")

if __name__ == "__main__":
    logger.warning("Always use `nb run` to start the bot instead of manually running!")
    nonebot.run()
