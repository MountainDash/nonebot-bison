import nonebot
from nonebot.adapters.cqhttp import Bot as CQHTTPBot

nonebot.init(command_start=[""])
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter('cqhttp', CQHTTPBot)

nonebot.load_builtin_plugins()
nonebot.load_plugins('src/plugins')

if __name__ == "__main__":
    nonebot.run(app="bot:app")
