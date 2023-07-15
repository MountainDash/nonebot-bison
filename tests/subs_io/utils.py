import json
from pathlib import Path

path = Path(__file__).parent / "static"


def get_json(file_name: str):
    """返回该目录下static目录下的<file_name>解析得到的json"""
    with open(path / file_name, encoding="utf8") as f:
        json_ = json.load(f)
        return json_


def get_file(file_name: str):
    """返回该目录下static目录下的<file_name>的文件内容"""
    with open(path / file_name, encoding="utf8") as f:
        file_text = f.read()
        return file_text
