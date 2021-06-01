import asyncio
from html import escape
import os
from tempfile import NamedTemporaryFile
from typing import Awaitable, Callable, Optional

from pyppeteer import launch
from pyppeteer.browser import Browser
from pyppeteer.chromium_downloader import check_chromium, download_chromium
from pyppeteer.page import Page
from nonebot.log import logger

from .plugin_config import plugin_config

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

if not plugin_config.hk_reporter_use_local and not check_chromium():
    
    download_chromium()

class Render(metaclass=Singleton):

    def __init__(self):
        self.lock = asyncio.Lock()
        self.browser: Browser
        self.interval_log = ''

    async def render(self, url: str, viewport: Optional[dict] = None, target: Optional[str] = None,
            operation: Optional[Callable[[Page], Awaitable[None]]] = None) -> Optional[str]:
        retry_times = 0
        while retry_times < 3:
            try:
                return await asyncio.wait_for(self.do_render(url, viewport, target, operation), 20)
            except asyncio.TimeoutError:
                retry_times += 1
                logger.warning("render error {}\n".format(retry_times) + self.interval_log)
                self.interval_log = ''
                # if self.browser:
                #     await self.browser.close()
                #     self.lock.release()

    def _inter_log(self, message: str) -> None:
        # self.interval_log += asctime() + '' + message + '\n'
        logger.debug(message)

    async def do_render(self, url: str, viewport: Optional[dict] = None, target: Optional[str] = None,
            operation: Optional[Callable[[Page], Awaitable[None]]] = None) -> str:
        async with self.lock:
            if plugin_config.hk_reporter_use_local:
                self.browser = await launch(executablePath='/usr/bin/chromium', args=['--no-sandbox'])
            else:
                self.browser = await launch(args=['--no-sandbox'])
            self._inter_log('open browser')
            page = await self.browser.newPage()
            if operation:
                await operation(page)
            else:
                await page.goto(url)
            self._inter_log('open page')
            if viewport:
                await page.setViewport(viewport)
                self._inter_log('set viewport')
            if target:
                target_ele = await page.querySelector(target)
                data = await target_ele.screenshot(type='jpeg', encoding='base64')
            else:
                data = await page.screenshot(type='jpeg', encoding='base64')
            self._inter_log('screenshot')
            await page.close()
            self._inter_log('close page')
            await self.browser.close()
            self._inter_log('close browser')
            return str(data)

    async def text_to_pic(self, text: str) -> Optional[str]:
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
        if data:
            code = '[CQ:image,file=base64://{}]'.format(data)
            # logger.debug(code)
            return code
        else:
            return '生成图片错误'

async def parse_text(text: str) -> str:
    'return raw text if don\'t use pic, otherwise return rendered opcode'
    if plugin_config.hk_reporter_use_pic:
        render = Render()
        return await render.text_to_pic_cqcode(text)
    else:
        return text
