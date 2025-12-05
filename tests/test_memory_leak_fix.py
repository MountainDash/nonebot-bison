"""测试 ProcessContext 内存泄漏修复"""

import gc

import httpx
from nonebug.app import App
import pytest


@pytest.mark.asyncio
async def test_context_cleanup(app: App):
    """测试 ProcessContext cleanup 方法是否正确关闭客户端"""
    from nonebot_bison.utils.context import ProcessContext
    from nonebot_bison.utils.site import DefaultClientManager

    context = ProcessContext(DefaultClientManager())

    # 获取多个客户端
    client1 = await context.get_client()
    client2 = await context.get_client_for_static()

    # 验证 client 被追踪
    assert len(context._clients) == 2
    assert not client1.is_closed
    assert not client2.is_closed

    # 调用 cleanup
    await context.cleanup()

    # 验证清理结果
    assert len(context._clients) == 0
    assert len(context.reqs) == 0
    assert client1.is_closed
    assert client2.is_closed


@pytest.mark.asyncio
async def test_no_memory_leak_after_multiple_fetches(app: App):
    """测试多次抓取后不会有内存泄漏"""
    from nonebot_bison.utils.context import ProcessContext
    from nonebot_bison.utils.site import DefaultClientManager

    # 初始状态
    gc.collect()
    initial_contexts = len([obj for obj in gc.get_objects() if isinstance(obj, ProcessContext)])
    initial_clients = len([obj for obj in gc.get_objects() if isinstance(obj, httpx.AsyncClient)])

    # 模拟10次抓取
    for _ in range(10):
        context = ProcessContext(DefaultClientManager())

        try:
            # 模拟平台获取 client
            await context.get_client()
            await context.get_client_for_static()
        finally:
            # 确保清理
            await context.cleanup()

    # 强制 GC
    gc.collect()

    # 检查最终状态
    final_contexts = len([obj for obj in gc.get_objects() if isinstance(obj, ProcessContext)])
    final_clients = len([obj for obj in gc.get_objects() if isinstance(obj, httpx.AsyncClient)])

    # 允许少量残留(最后一个可能还没释放)
    leaked_contexts = final_contexts - initial_contexts
    leaked_clients = final_clients - initial_clients

    # 严格检查: 泄漏应该很少
    assert leaked_contexts <= 1, f"泄漏了 {leaked_contexts} 个 ProcessContext (预期 ≤ 1)"
    assert leaked_clients <= 2, f"泄漏了 {leaked_clients} 个 AsyncClient (预期 ≤ 2)"


@pytest.mark.asyncio
async def test_cleanup_on_exception(app: App):
    """测试异常情况下也能正确清理"""
    from nonebot_bison.utils.context import ProcessContext
    from nonebot_bison.utils.site import DefaultClientManager

    context = ProcessContext(DefaultClientManager())

    try:
        client = await context.get_client()
        assert not client.is_closed

        # 模拟异常
        raise ValueError("测试异常")

    except ValueError:
        pass  # 捕获异常
    finally:
        # 即使有异常,也应该清理
        await context.cleanup()

    # 验证客户端被关闭
    assert len(context._clients) == 0
    assert client.is_closed
