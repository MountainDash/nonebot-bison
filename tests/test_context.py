import httpx
from nonebug.app import App
import respx


@respx.mock
async def test_http_error(app: App):
    from nonebot_bison.utils import DefaultClientManager, ProcessContext, http_client

    example_route = respx.get("https://example.com")
    example_route.mock(httpx.Response(403, json={"error": "gg"}))

    ctx = ProcessContext(DefaultClientManager())
    async with http_client() as client:
        ctx._register_to_client(client)
        await client.get("https://example.com")

    assert ctx.gen_req_records() == [
        "https://example.com Headers({'host': 'example.com', 'accept': '*/*', 'accept-encoding': 'gzip, deflate',"
        " 'connection': 'keep-alive', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0'}) | [403] Headers({'content-length': '"
        "14', 'content-type':"
        ' \'application/json\'}) {"error":"gg"}'
    ]
