from httpx import Response
from nonebot import logger

from .exception import CeobeResponseError
from .models import ResponseModel, CookieIdResponse


def process_response(response: Response, parse_model: type[ResponseModel]) -> ResponseModel:
    response.raise_for_status()
    logger.trace(f"小刻食堂请求结果: {response.json().get('message')} {parse_model=}")

    try:
        data = parse_model.parse_obj(response.json())
    except Exception as e:
        raise CeobeResponseError(f"解析小刻食堂响应失败: {e}")

    if not isinstance(data, CookieIdResponse) and data.code != 0:
        raise CeobeResponseError(f"获取饼数据失败: {data.message}")
    return data
