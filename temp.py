from copy import deepcopy
from dataclasses import dataclass, field

from typing_extensions import Self


@dataclass
class info:
    name: str
    id: int
    age: int
    sex: str
    color: str = field(default="")

    def __init__(cls, raw: dict):
        cls.__dict__.update(raw)

    def test(cls, old_info: Self) -> bool:
        pass


if __name__ == "__main__":
    raw_info: dict = {
        "name": "lily",
        "id": 2998,
        "age": 32,
        "sex": "1223",
        "family": "oo",
    }

    test_info = info(raw_info)
    print(test_info)
    test_info.color = "black"
    test_info2 = deepcopy(test_info)
    print(test_info2)
    test_info.test(test_info2)
    raw_info["name"] = "lilei"
    raw2 = deepcopy(raw_info)
    tt = info(raw2)
    print(tt)
