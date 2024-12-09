from nonebug import App


async def test_webui_auth(app: App):
    from nonebot_bison.admin_page.token_manager import token_manager

    token = token_manager.get_user_token(("10001", "test"))

    async with app.test_server() as ctx:
        client = ctx.get_client()

        resp = await client.get(f"/bison/api/auth?token={token}")

        assert resp.status_code == 200

        data = resp.json()
        assert data["type"] == "admin"
        assert data["name"] == "test"
        assert data["id"] == 10001
        assert "token" in data
