import nonebot
from pyppeteer import launch
from html import escape
from hashlib import sha256

from . import plugin_config

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

supported_target_type = ('weibo', 'bilibili', 'rss')

class Render(metaclass=Singleton):

    def __init__(self):
        self.page = None

    async def init(self):
        browser = await launch(execublePath='/usr/bin/chromium')
        self.page = await browser.newPage()

    async def text_to_pic(self, text: str) -> str:
        hash_text = sha256(text.encode()).hexdigest()[:20]
        lines = text.split('\n')
        parsed_lines = list(map(lambda x: '<p>{}</p>'.format(escape(x)), lines))
        html_text = '<div style="width:17em;padding:1em">{}</div>'.format(''.join(parsed_lines))
        with open('/tmp/text-{}.html'.format(hash_text), 'w') as f:
            f.write(html_text)
        await self.page.goto('file:///tmp/text-{}.html'.format(hash_text))
        div = await self.page.querySelector('div')
        path = '/tmp/img-{}.png'.format(hash_text)
        await div.screenshot(path=path)
        return path

    async def text_to_pic_cqcode(self, text:str) -> str:
        path = await self.text_to_pic(text)
        return '[CQ:image,file=file://{}]'.format(path)

async def _start():
    r = Render()
    await r.init()

nonebot.get_driver().on_startup(_start)
async def parse_text(text: str):
    if plugin_config.use_pic:
        r = Render()
        return await r.text_to_pic_cqcode(text)
    else:
        return text
         
