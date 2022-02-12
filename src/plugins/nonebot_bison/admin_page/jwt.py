import datetime
import random
import string
from typing import Optional

import jwt

_key = "".join(random.SystemRandom().choice(string.ascii_letters) for _ in range(16))


def pack_jwt(obj: dict) -> str:
    return jwt.encode(
        {"exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1), **obj},
        _key,
        algorithm="HS256",
    )


def load_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _key, algorithms=["HS256"])
    except:
        return None
