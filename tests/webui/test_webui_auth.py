from nonebug import App


async def test_webui_refresh_token(app: App):
    """利用 Refresh Token 获取 Access Token

    https://app.apifox.com/link/project/4920109/apis/api-199770042
    """

    async with app.test_server() as ctx:
        client = ctx.get_client()

        resp = await client.get("/bison/api/refresh", json={"refresh_token": "test"})
        assert resp.status_code == 200

        data = resp.json()
        assert "access_token" in data
