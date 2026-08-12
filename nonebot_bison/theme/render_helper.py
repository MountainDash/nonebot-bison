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
    from nonebot_plugin_htmlrender import render_html

    """html转图片，使用render_html渲染"""
    # 兼容旧调用：0.7 的 get_new_page 接受 viewport/base_url 等页面参数，
    # 0.8 的 render_html 只接受中立的 width/height，浏览器参数不再使用
    width = kwargs.pop("width", None) or kwargs.pop("viewport", {}).get("width", 500)
    kwargs.pop("height", None)
    base_url = kwargs.pop("base_url", None)
    if kwargs:
        from nonebot.log import logger

        logger.debug(f"html_to_pic: 忽略不支持的页面参数 {list(kwargs)}")
    return bytes(
        await render_html(
            html,
            width=width,
            height=None,
            device_pixel_ratio=device_scale_factor,
            image_format=type,
            quality=quality,
            base_url=base_url,
            timeout_seconds=(screenshot_timeout / 1000) if screenshot_timeout else None,
        )
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
    """使用jinja2模板引擎通过html生成图片

    Args:
        screenshot_timeout (float, optional): 渲染超时时间，默认30000ms
        template_path (str): 模板路径
        template_name (str): 模板名
        templates (Dict[Any, Any]): 模板内参数 如: {"name": "abc"}
        filters (Optional[Dict[str, Any]]): 自定义过滤器
        pages (Optional[Dict[Any, Any]]): 兼容旧参数，仅使用其中的 viewport 宽度
            Defaults to {"viewport": {"width": 500}}
        wait (int, optional): 兼容旧参数，0.8 不再支持，忽略. Defaults to 0.
        type (Literal["jpeg", "png"]): 图片类型, 默认 png
        quality (int, optional): 图片质量 0-100 当为`png`时无效
        device_scale_factor: 缩放比例,类型为float,值越大越清晰
    Returns:
        bytes: 图片 可直接发送
    """
    if pages is None:
        pages = {
            "viewport": {"width": 500},
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
