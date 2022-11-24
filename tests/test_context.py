import httpx
import respx
from nonebug.app import App


@respx.mock
async def test_http_error(app: App):
    from nonebot_bison.utils import ProcessContext, http_client

    example_route = respx.get("https://example.com")
    example_route.mock(httpx.Response(403, json={"error": "gg"}))

    ctx = ProcessContext()
    async with http_client() as client:
        ctx.register_to_client(client)
        await client.get("https://example.com")

    assert ctx.gen_req_records() == [
        "https://example.com Headers({'host': 'example.com', 'accept': '*/*', 'accept-encoding': 'gzip, deflate', 'connection': 'keep-alive', 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}) | [403] Headers({'content-length': '15', 'content-type': 'application/json'}) {\"error\": \"gg\"}"
    ]
