import hashlib
import hmac
import json
import time


def generate_signature(
    token: str,
    path: str,
    params: dict,
    dId: str,
    platform: str = "3",
    vName: str = "1.0.0",
    timestamp: str | None = None,
) -> tuple[str, dict[str, str]]:
    """
    修改后的签名生成函数:
    1. 不再使用硬编码的 SECRET。
    2. 使用传入的 token 作为 HMAC 的 Key。
    3. 保持 Path + Query + Timestamp + HeaderJSON 的无缝拼接逻辑。
    """
    if not timestamp:
        timestamp = str(int(time.time()))

    # 1. 构造参与签名的 Header 字典
    header_ca = {"platform": platform, "timestamp": timestamp, "dId": dId, "vName": vName}

    # 2. 紧凑 JSON 序列化 (无空格)
    header_str = json.dumps(header_ca, separators=(",", ":"), ensure_ascii=False)

    # 3. 构建查询字符串内容 (无 '?' 拼接)
    query_content = ""
    if params:
        query_content = "&".join([f"{k}={v}" for k, v in params.items()])

    # 4. 构造签名原型字符串
    sign_string = f"{path}{query_content}{timestamp}{header_str}"

    # 5. 加密逻辑 (HMAC-SHA256 + MD5)
    # 修改处:这里使用 token.encode('utf-8') 作为 Key
    key_bytes = token.encode("utf-8")
    sign_bytes = sign_string.encode("utf-8")

    # 第一层:HMAC-SHA256
    hmac_result = hmac.new(key_bytes, sign_bytes, hashlib.sha256).hexdigest()

    # 第二层:MD5
    sign = hashlib.md5(hmac_result.encode("utf-8")).hexdigest()

    return sign, header_ca


# --- 业务接口保持不变 ---


def generate_signature_for_user_items(token, userId, dId, **kwargs):
    path = "/web/v1/user/items"
    params = {"pageSize": kwargs.get("pageSize", 10), "userId": userId, "sortType": kwargs.get("sortType", 2)}
    return generate_signature(token, path, params, dId)


def generate_signature_for_user(token, userId, dId):
    path = "/web/v1/user"
    params = {"id": userId}
    return generate_signature(token, path, params, dId)


def generate_signature_for_item(token, itemId, dId):
    path = "/web/v1/item"
    params = {"id": itemId}
    return generate_signature(token, path, params, dId)


def generate_signature_for_game(token, dId):
    path = "/web/v1/game"
    params = {}
    return generate_signature(token, path, params, dId)
