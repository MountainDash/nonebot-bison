from base64 import b64encode

from httpx import AsyncClient, Response


class ProcessContext:
    reqs: list[Response]

    def __init__(self) -> None:
        self.reqs = []

    def log_response(self, resp: Response):
        self.reqs.append(resp)

    def register_to_client(self, client: AsyncClient):
        async def _log_to_ctx(r: Response):
            self.log_response(r)

        hooks = {
            "response": [_log_to_ctx],
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
                log_content = f"{req.request.url} {req.request.headers} | [{req.status_code}] {req.headers} b64encoded: {b64encode(req.content[:50]).decode()}"
            res.append(log_content)
        return res
