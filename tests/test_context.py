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


@respx.mock
async def test_no_content_type_utf8(app: App):
    """Test handling of responses without content-type header but with UTF-8 decodable content."""
    from nonebot_bison.utils import DefaultClientManager, ProcessContext, http_client

    example_route = respx.get("https://example.com/utf8")
    # Response without content-type header but with UTF-8 text content
    example_route.mock(httpx.Response(200, content=b"UTF-8 text content"))

    ctx = ProcessContext(DefaultClientManager())
    async with http_client() as client:
        ctx._register_to_client(client)
        await client.get("https://example.com/utf8")

    records = ctx.gen_req_records()
    assert len(records) == 1
    # Should print content since it's UTF-8 decodable
    assert "UTF-8 text content" in records[0]
    assert "b64encoded" not in records[0]


@respx.mock
async def test_no_content_type_binary(app: App):
    """Test handling of responses without content-type header and binary content."""
    from nonebot_bison.utils import DefaultClientManager, ProcessContext, http_client

    example_route = respx.get("https://example.com/binary")
    # Response without content-type header and binary content that cannot be decoded as UTF-8
    example_route.mock(httpx.Response(200, content=b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"))

    ctx = ProcessContext(DefaultClientManager())
    async with http_client() as client:
        ctx._register_to_client(client)
        await client.get("https://example.com/binary")

    records = ctx.gen_req_records()
    assert len(records) == 1
    # Should use base64 encoding for binary content
    assert "b64encoded" in records[0]
    assert "iVBORw0K" in records[0]  # Base64 of PNG header
