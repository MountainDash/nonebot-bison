from nonebug import App

from .utils import authenticate_user


async def test_webui_me(app: App):
    """获取当前登录的用户名

    https://app.apifox.com/link/project/4920109/apis/api-242059875
    """

    token = authenticate_user("10001")

    async with app.test_server() as ctx:
        client = ctx.get_client()
        client.headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/bison/api/me")
        assert resp.status_code == 200

        assert resp.json() == {"name": "string", "role": "superuser", "bot": "string"}
