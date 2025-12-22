from base64 import b64encode

from httpx import AsyncClient, Response

from nonebot_bison.types import Target

from .site import ClientManager


class ProcessContext:
    reqs: list[Response]
    _client_mgr: ClientManager
    _clients: list[AsyncClient]
    _client: AsyncClient | None
    _static_client: AsyncClient | None

    def __init__(self, client_mgr: ClientManager) -> None:
        self.reqs = []
        self._client_mgr = client_mgr
        self._clients = []
        self._client = None
        self._static_client = None

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
        if self._client is None or self._client.is_closed:
            client = await self._client_mgr.get_client(target)
            self._register_to_client(client)
            self._clients.append(client)
            self._client = client
        return self._client

    async def get_client_for_static(self) -> AsyncClient:
        if self._static_client is None or self._static_client.is_closed:
            client = await self._client_mgr.get_client_for_static()
            self._register_to_client(client)
            self._clients.append(client)
            self._static_client = client
        return self._static_client

    async def refresh_client(self):
        await self._client_mgr.refresh_client()
        # Invalidate cached clients after refresh
        self._client = None
        self._static_client = None

    async def cleanup(self):
        """关闭所有创建的 HTTP 客户端,释放资源"""
        for client in self._clients:
            await client.aclose()
        self._clients.clear()
        self.reqs.clear()
        self._client = None
        self._static_client = None

    def __deepcopy__(self, memo):
        """
        自定义深拷贝行为,跳过不可序列化的字段。

        _clients 和 reqs 包含 AsyncClient 和 Response 对象,这些对象内部有线程锁,
        无法被 pickle/deepcopy。由于 ProcessContext 主要用于请求追踪,
        深拷贝时创建一个新的空实例是合理的。
        """
        # 创建新实例,使用相同的 client_mgr
        new_instance = ProcessContext(self._client_mgr)
        memo[id(self)] = new_instance
        return new_instance
