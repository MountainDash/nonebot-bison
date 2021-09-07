import asyncio
import base64
from html import escape
from typing import Awaitable, Callable, Optional
from urllib.parse import quote
from nonebot.adapters.cqhttp.message import MessageSegment

from nonebot.log import logger
from pyppeteer import connect, launch
from pyppeteer.browser import Browser
from pyppeteer.page import Page

from .plugin_config import plugin_config

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Render(metaclass=Singleton):

    def __init__(self):
        self.lock = asyncio.Lock()
        self.browser: Browser
        self.interval_log = ''
        self.remote_browser = False

    async def get_browser(self) -> Browser:
        if plugin_config.hk_reporter_browser:
            if plugin_config.hk_reporter_browser.startswith('local:'):
                path = plugin_config.hk_reporter_browser.split('local:', 1)[1]
                return await launch(executablePath=path, args=['--no-sandbox'])
            if plugin_config.hk_reporter_browser.startswith('ws:'):
                self.remote_browser = True
                return await connect(browserWSEndpoint=plugin_config.hk_reporter_browser)
            raise RuntimeError('HK_REPORTER_BROWSER error')
        if plugin_config.hk_reporter_use_local:
            return await launch(executablePath='/usr/bin/chromium', args=['--no-sandbox'])
        return await launch(args=['--no-sandbox'])

    async def close_browser(self):
        if not self.remote_browser:
            await self.browser.close()

    async def render(self, url: str, viewport: Optional[dict] = None, target: Optional[str] = None,
            operation: Optional[Callable[[Page], Awaitable[None]]] = None) -> Optional[bytes]:
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
            operation: Optional[Callable[[Page], Awaitable[None]]] = None) -> Optional[bytes]:
        async with self.lock:
            self.browser = await self.get_browser()
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
                if not target_ele:
                    return None
                data = await target_ele.screenshot(type='jpeg', encoding='binary')
            else:
                data = await page.screenshot(type='jpeg', encoding='binary')
            self._inter_log('screenshot')
            await page.close()
            self._inter_log('close page')
            await self.close_browser()
            self._inter_log('close browser')
            assert(isinstance(data, bytes))
            return data

    async def text_to_pic(self, text: str) -> Optional[bytes]:
        lines = text.split('\n')
        parsed_lines = list(map(lambda x: '<p>{}</p>'.format(escape(x)), lines))
        html_text = '<div style="width:17em;padding:1em">{}</div>'.format(''.join(parsed_lines))
        url = 'data:text/html;charset=UTF-8;base64,{}'.format(base64.b64encode(html_text.encode()).decode())
        data = await self.render(url, target='div')
        return data

    async def text_to_pic_cqcode(self, text:str) -> MessageSegment:
        data = await self.text_to_pic(text)
        # logger.debug('file size: {}'.format(len(data)))
        if data:
            # logger.debug(code)
            return MessageSegment.image(data)
        else:
            return MessageSegment.text('生成图片错误')

async def parse_text(text: str) -> MessageSegment:
    'return raw text if don\'t use pic, otherwise return rendered opcode'
    if plugin_config.hk_reporter_use_pic:
        render = Render()
        return await render.text_to_pic_cqcode(text)
    else:
        return MessageSegment.text(text)
