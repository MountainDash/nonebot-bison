from datetime import datetime, timezone, timedelta

from nonebot import logger


def timestamp_to_str(timestamp: int, offset_hour: int = 8) -> str:
    """将时间戳转换为字符串"""

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone(timedelta(hours=offset_hour)),
    ).strftime("%Y-%m-%d %H:%M:%S")


def _half_width_len(text: str):
    """
    计算字符串的半角长度
    """
    length = 0
    for char in text:
        if "\u0020" <= char <= "\u007e" or "\uff61" <= char <= "\uff9f" or "\uffa0" <= char <= "\uffdc":
            # 半角字符：ASCII、片假半角、韩文半角
            length += 1
        else:
            # 全角字符
            length += 2
    return length


def _cut_text_with_half_width(text: str, max_half_width: int, ellipsis: bool = True) -> str:
    """
    按照半角长度截断字符串
    """
    text_half_width = 0
    index = 0
    for char in text:
        index += 1
        if "\u0020" <= char <= "\u007e" or "\uff61" <= char <= "\uff9f" or "\uffa0" <= char <= "\uffdc":
            # 半角字符：ASCII、片假半角、韩文半角
            text_half_width += 1
        else:
            # 全角字符
            text_half_width += 2

        logger.trace(f"char: {char}, text_half_width: {text_half_width}")

        if text_half_width >= max_half_width:
            text = (text[: index - 1] + "...") if ellipsis else text[: index - 1]
            logger.trace(f"cut text:\n{text}")
            break

    return text


def _check_text_overflow(text: str, max_half_width: int, max_half_width_per_line: int, max_line: int) -> str:
    """
    检查文字内容是否会超出css盒子
    """

    text = _cut_text_with_half_width(text, max_half_width, ellipsis=False)
    logger.trace(f"text: \n{text}")

    text_lines = [x.rstrip() for x in text.split("\n")]
    logger.trace(text_lines)

    if len(text_lines) == 1:
        return text

    remain_line = max_line
    show_lines = []
    for line in text_lines:
        logger.trace(f"line: {line}")
        hold_line = _half_width_len(line) // max_half_width_per_line + 1

        if remain_line > hold_line:
            logger.trace(f"remain_line: {remain_line}, hold_line: {hold_line}\nappend: {line}")
            show_lines.append(line)
            remain_line -= hold_line
        else:
            if _half_width_len(line) > max_half_width_per_line:
                show_line = _cut_text_with_half_width(line, max_half_width_per_line)
                logger.trace(f"remain_line: {remain_line}, hold_line: {hold_line}\nappend: {show_line}, finish")
                show_lines.append(show_line)
                break
            elif len(text_lines) > 3:
                show_line = line + "..."
                logger.trace(f"remain_line: {remain_line}, hold_line: {hold_line}\nappend: {show_line}, finish")
                show_lines.append(show_line)
                break
            else:
                logger.trace(f"remain_line: {remain_line}, hold_line: {hold_line}\nappend: {line}, finish")
                show_lines.append(line)
                break

    return "<br>".join(show_lines)
