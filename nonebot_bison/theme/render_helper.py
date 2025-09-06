from typing import Any, Literal

import jinja2


async def html_to_pic(
    html: str,
    wait: int = 0,
    type: Literal["jpeg", "png"] = "png",
    quality: int | None = None,
    device_scale_factor: float = 2,
    screenshot_timeout: float | None = 30_000,
    **kwargs,
) -> bytes:
    from nonebot_plugin_htmlrender.browser import get_new_page

    """html转图片，使用about:blank而不是file://路径"""
    async with get_new_page(device_scale_factor, **kwargs) as page:
        await page.goto("about:blank")
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_timeout(wait)
        return await page.screenshot(
            full_page=True,
            type=type,
            quality=quality,
            timeout=screenshot_timeout,
        )


async def template_to_pic(
    template_path: str,
    template_name: str,
    templates: dict[Any, Any],
    filters: dict[str, Any] | None = None,
    pages: dict[Any, Any] | None = None,
    wait: int = 0,
    type: Literal["jpeg", "png"] = "png",
    quality: int | None = None,
    device_scale_factor: float = 2,
    screenshot_timeout: float | None = 30_000,
) -> bytes:
    """使用jinja2模板引擎通过html生成图片，使用about:blank导航

    Args:
        screenshot_timeout (float, optional): 截图超时时间，默认30000ms
        template_path (str): 模板路径
        template_name (str): 模板名
        templates (Dict[Any, Any]): 模板内参数 如: {"name": "abc"}
        filters (Optional[Dict[str, Any]]): 自定义过滤器
        pages (Optional[Dict[Any, Any]]): 网页参数 Defaults to
            {"viewport": {"width": 500, "height": 10}}
        wait (int, optional): 网页载入等待时间. Defaults to 0.
        type (Literal["jpeg", "png"]): 图片类型, 默认 png
        quality (int, optional): 图片质量 0-100 当为`png`时无效
        device_scale_factor: 缩放比例,类型为float,值越大越清晰
    Returns:
        bytes: 图片 可直接发送
    """
    if pages is None:
        pages = {
            "viewport": {"width": 500, "height": 10},
        }

    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_path),
        enable_async=True,
    )

    if filters:
        for filter_name, filter_func in filters.items():
            template_env.filters[filter_name] = filter_func

    template = template_env.get_template(template_name)

    return await html_to_pic(
        html=await template.render_async(**templates),
        wait=wait,
        type=type,
        quality=quality,
        device_scale_factor=device_scale_factor,
        screenshot_timeout=screenshot_timeout,
        **pages,
    )
