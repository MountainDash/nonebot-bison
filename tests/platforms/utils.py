import json
from pathlib import Path

path = Path(__file__).parent / "static"


def get_json(file_name: str):
    with open(path / file_name, encoding="utf8") as f:
        file_text = f.read()
        return json.loads(file_text)


def get_file(file_name: str):
    with open(path / file_name, encoding="utf8") as f:
        file_text = f.read()
        return file_text


def get_bytes(file_name: str):
    with open(path / file_name, "rb") as f:
        return f.read()
