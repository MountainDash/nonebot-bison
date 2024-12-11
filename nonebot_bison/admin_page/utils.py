from functools import wraps

from nonebot.drivers import Request, Response

from .jwt import load_jwt


async def is_login(request: Request):
    # TODO: 检查是否登录，不知道权限该怎么控制。
    headers = request.headers
    token = headers.get("Authorization", "").removeprefix("Bearer ")
    data = load_jwt(token)
    return data is not None


def login_required(func):
    """需要登录验证装饰器"""

    @wraps(func)
    async def wrapper(request: Request) -> Response:
        if not await is_login(request):
            return Response(401, content="Unauthorized")
        return await func(request)

    return wrapper
