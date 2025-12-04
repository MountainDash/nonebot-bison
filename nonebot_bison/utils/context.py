from base64 import b64encode

from httpx import AsyncClient, Response
from nonebot.log import logger

from nonebot_bison.types import Target

from .site import ClientManager


class ProcessContext:
    reqs: list[Response]
    _client_mgr: ClientManager
    _clients: list[AsyncClient]

    def __init__(self, client_mgr: ClientManager) -> None:
        self.reqs = []
        self._client_mgr = client_mgr
        self._clients = []
        logger.trace("ProcessContext 已创建")

    def _log_response(self, resp: Response):
        self.reqs.append(resp)

    def _register_to_client(self, client: AsyncClient):
        async def _log_to_ctx(r: Response):
            self._log_response(r)

        existing_hooks = client.event_hooks["response"]
        hooks = {
            "response": [*existing_hooks, _log_to_ctx],
        }
        client.event_hooks = hooks

    def _should_print_content(self, r: Response) -> bool:
        content_type = r.headers["content-type"]
        if content_type.startswith("text"):
            return True
        if "json" in content_type:
            return True
        return False

    def gen_req_records(self) -> list[str]:
        res = []
        for req in self.reqs:
            if self._should_print_content(req):
                log_content = f"{req.request.url} {req.request.headers} | [{req.status_code}] {req.headers} {req.text}"
            else:
                log_content = (
                    f"{req.request.url} {req.request.headers} | [{req.status_code}] {req.headers} "
                    f"b64encoded: {b64encode(req.content[:50]).decode()}"
                )
            res.append(log_content)
        return res

    async def get_client(self, target: Target | None = None) -> AsyncClient:
        client = await self._client_mgr.get_client(target)
        self._register_to_client(client)
        self._clients.append(client)
        logger.trace(f"ProcessContext 创建新 HTTP 客户端，当前总数: {len(self._clients)}")
        return client

    async def get_client_for_static(self) -> AsyncClient:
        client = await self._client_mgr.get_client_for_static()
        self._register_to_client(client)
        self._clients.append(client)
        logger.trace(f"ProcessContext 创建静态资源客户端，当前总数: {len(self._clients)}")
        return client

    async def refresh_client(self):
        await self._client_mgr.refresh_client()

    async def cleanup(self):
        """关闭所有创建的 AsyncClient 并清理资源"""
        client_count = len(self._clients)
        response_count = len(self.reqs)

        logger.info(f"ProcessContext 开始清理: {client_count} 个 HTTP 客户端, {response_count} 个响应记录")

        # 关闭所有客户端
        closed_count = 0
        failed_count = 0
        for idx, client in enumerate(self._clients):
            try:
                await client.aclose()
                closed_count += 1
                logger.trace(f"HTTP 客户端 {idx + 1}/{client_count} 已关闭")
            except Exception as e:
                failed_count += 1
                logger.warning(
                    f"关闭 HTTP 客户端 {idx + 1}/{client_count} 失败: {type(e).__name__}: {e}",
                    exc_info=False,
                )

        # 清理列表
        self._clients.clear()
        self.reqs.clear()

        # 输出清理结果
        logger.info(
            f"ProcessContext 清理完成: 成功关闭 {closed_count} 个客户端, "
            f"失败 {failed_count} 个, 已释放 {response_count} 个响应记录"
        )
