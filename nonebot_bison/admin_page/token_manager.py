from datetime import timedelta
import random
import string

from expiringdictx import ExpiringDict


class TokenManager:
    def __init__(self):
        self.token_manager = ExpiringDict[str, tuple](capacity=100, default_age=timedelta(minutes=10))

    def get_user(self, token: str) -> tuple | None:
        res = self.token_manager.get(token)
        assert res is None or isinstance(res, tuple)
        return res

    def save_user(self, token: str, qq: tuple) -> None:
        self.token_manager[token] = qq

    def get_user_token(self, qq: tuple) -> str:
        token = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        self.save_user(token, qq)
        return token


token_manager = TokenManager()
