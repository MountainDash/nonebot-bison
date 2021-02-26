import os
import asyncio
from typing import Optional
import nonebot
from nonebot import logger
import base64
from pyppeteer import launch
from html import escape
from hashlib import sha256

from .plugin_config import plugin_config

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

supported_target_type = ('weibo', 'bilibili', 'rss')

class Render(metaclass=Singleton):

    def __init__(self):
        self.lock = asyncio.Lock()

    async def render(self, url: str, viewport: Optional[dict] = None, target: Optional[str] = None) -> str:
        async with self.lock:
            if plugin_config.hk_reporter_use_local:
                browser = await launch(executablePath='/usr/bin/chromium', args=['--no-sandbox'])
            else:
                browser = await launch(args=['--no-sandbox'])
            page = await browser.newPage()
            await page.goto(url)
            if viewport:
                await page.setViewport(viewport)
            if target:
                target_ele = await page.querySelector(target)
                data = await target_ele.screenshot(type='jpeg', encoding='base64')
            else:
                data = await page.screenshot(type='jpeg', encoding='base64')
            await page.close()
            await browser.close()
            return str(data)

    async def text_to_pic(self, text: str) -> str:
        hash_text = sha256(text.encode()).hexdigest()[:20]
        lines = text.split('\n')
        parsed_lines = list(map(lambda x: '<p>{}</p>'.format(escape(x)), lines))
        html_text = '<div style="width:17em;padding:1em">{}</div>'.format(''.join(parsed_lines))
        with open('/tmp/text-{}.html'.format(hash_text), 'w') as f:
            f.write(html_text)
        data = await self.render('file:///tmp/text-{}.html'.format(hash_text), target='div')
        os.remove('/tmp/text-{}.html'.format(hash_text))
        return data

    async def text_to_pic_cqcode(self, text:str) -> str:
        data = await self.text_to_pic(text)
        # logger.debug('file size: {}'.format(len(data)))
        code = '[CQ:image,file=base64://{}]'.format(data)
        # logger.debug(code)
        return code

async def parse_text(text: str):
    if plugin_config.hk_reporter_use_pic:
        r = Render()
        return await r.text_to_pic_cqcode(text)
    else:
        return text

