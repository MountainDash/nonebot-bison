import random
import string
from typing import Optional

from expiringdict import ExpiringDict


class TokenManager:
    def __init__(self):
        self.token_manager = ExpiringDict(max_len=100, max_age_seconds=60 * 10)

    def get_user(self, token: str) -> Optional[tuple]:
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
