def text_fletten(text: str, *, banned: str = "\n\r\t", replace: str = " ") -> str:
    """将文本中的格式化字符去除"""
    return "".join(c if c not in banned else replace for c in text)
