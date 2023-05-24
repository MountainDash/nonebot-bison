import json
from pathlib import Path

path = Path(__file__).parent / "static"


def get_json(file_name: str):
    with open(path / file_name, "r", encoding="utf8") as f:
        file_text = f.read()
        return json.loads(file_text)


def get_file(file_name: str, mode="r", encoding: str | None = "utf8"):
    with open(path / file_name, mode=mode, encoding=encoding) as f:
        file_text = f.read()
        return file_text
