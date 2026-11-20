"""workspace 的烟雾测试：两个包都能被导入。"""


def test_courier_imports() -> None:
    import courier

    assert courier.__all__ == []


def test_bison_imports() -> None:
    import bison

    assert bison.__all__ == []
