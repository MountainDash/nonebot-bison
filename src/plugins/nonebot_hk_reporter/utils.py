import os
import asyncio
from typing import Optional
import nonebot
from nonebot import logger
import base64
from pyppeteer import launch
from pyppeteer.chromium_downloader import check_chromium, download_chromium
from html import escape
from hashlib import sha256
from tempfile import NamedTemporaryFile

from .plugin_config import plugin_config

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

supported_target_type = ('weibo', 'bilibili', 'rss')

if not plugin_config.hk_reporter_use_local and not check_chromium():
    os.environ['PYPPETEER_DOWNLOAD_HOST'] = 'http://npm.taobao.org/mirrors'
    download_chromium()

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
        lines = text.split('\n')
        parsed_lines = list(map(lambda x: '<p>{}</p>'.format(escape(x)), lines))
        html_text = '<div style="width:17em;padding:1em">{}</div>'.format(''.join(parsed_lines))
        with NamedTemporaryFile('wt', suffix='.html', delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(html_text)
        data = await self.render('file://{}'.format(tmp_path), target='div')
        os.remove(tmp_path)
        return data

    async def text_to_pic_cqcode(self, text:str) -> str:
        data = await self.text_to_pic(text)
        # logger.debug('file size: {}'.format(len(data)))
        code = '[CQ:image,file=base64://{}]'.format(data)
        # logger.debug(code)
        return code

async def parse_text(text: str) -> str:
    'return raw text if don\'t use pic, otherwise return rendered opcode'
    if plugin_config.hk_reporter_use_pic:
        render = Render()
        return await render.text_to_pic_cqcode(text)
    else:
        return text
