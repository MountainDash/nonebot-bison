import typing

import pytest
from httpx import AsyncClient
from nonebug.app import App


@pytest.mark.asyncio
@pytest.mark.render
async def test_render(app: App):
    from nonebot_bison.plugin_config import plugin_config
    from nonebot_bison.utils import parse_text

    plugin_config.bison_use_pic = True

    res = await parse_text(
        """a\nbbbbbbbbbbbbbbbbbbbbbb\ncd
<h1>中文</h1>
VuePress 由两部分组成：第一部分是一个极简静态网站生成器

(opens new window)，它包含由 Vue 驱动的主题系统和插件 API，另一个部分是为书写技术文档而优化的默认主题，它的诞生初衷是为了支持 Vue 及其子项目的文档需求。

每一个由 VuePress 生成的页面都带有预渲染好的 HTML，也因此具有非常好的加载性能和搜索引擎优化（SEO）。同时，一旦页面被加载，Vue 将接管这些静态内容，并将其转换成一个完整的单页应用（SPA），其他的页面则会只在用户浏览到的时候才按需加载。
"""
    )


@pytest.mark.asyncio
@pytest.mark.render
async def test_arknights(app: App):
    from nonebot_bison.platform.arknights import Arknights

    ak = Arknights(AsyncClient())
    res = await ak.parse(
        {"webUrl": "https://ak.hycdn.cn/announce/IOS/announcement/854_1644580545.html"}
    )
