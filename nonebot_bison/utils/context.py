from base64 import b64encode

from httpx import AsyncClient, Response

from nonebot_bison.types import Target

from .site import ClientManager


class ProcessContext:
    reqs: list[Response]
    _client_mgr: ClientManager

    def __init__(self, client_mgr: ClientManager) -> None:
        self.reqs = []
        self._client_mgr = client_mgr

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
        return client

    async def get_client_for_static(self) -> AsyncClient:
        client = await self._client_mgr.get_client_for_static()
        self._register_to_client(client)
        return client

    async def refresh_client(self):
        await self._client_mgr.refresh_client()
