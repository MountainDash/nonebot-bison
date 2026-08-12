"""
sk_token.py - 动态时间校准修复版
实现了基于 32.js 逆向逻辑的时间同步机制,解决 401 签名失效问题。
"""

import asyncio
from dataclasses import dataclass
import logging
import time

import aiohttp

from .skland_sign import generate_signature

logger = logging.getLogger(__name__)
_default_token_manager = None


@dataclass
class TokenInfo:
    """Token信息"""

    token: str
    timestamp: int  # 获取Token时的本地时间戳
    server_time_offset: int = 0  # 核心:服务器与本地时间的偏移量 (serverTime - clientTime)
    is_valid: bool = True

    @property
    def age(self) -> int:
        """token年龄(秒)"""
        return int(time.time()) - self.timestamp


class SkTokenManager:
    """Skland Token管理器 - 动态同步版"""

    def __init__(
        self,
        dId: str,
        platform: str = "3",
        vName: str = "1.0.0",
        refresh_url: str = "https://zonai.skland.com/web/v1/auth/refresh",
    ):
        self.dId = dId
        self.platform = platform
        self.vName = vName
        self.refresh_url = refresh_url
        self.current_token: TokenInfo | None = None
        self._refresh_lock = asyncio.Lock()

        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
        logger.info(f"Token管理器初始化完成,dId: {dId[:20]}...")

    async def get_token_info(self, force_refresh: bool = False) -> TokenInfo | None:
        """获取完整的TokenInfo对象,包含时间偏移"""
        need_refresh = (
            force_refresh
            or self.current_token is None
            or not self.current_token.is_valid
            or self.current_token.age > 3600
        )

        if need_refresh:
            async with self._refresh_lock:
                if need_refresh or self.current_token is None:
                    await self._refresh_token()

        return self.current_token

    async def get_token(self, force_refresh: bool = False) -> str:
        """获取有效token字符串"""
        info = await self.get_token_info(force_refresh)
        if info is None:
            raise RuntimeError("Failed to get token info")
        return info.token

    async def _refresh_token(self) -> None:
        """
        刷新token并同步服务器时间
        """
        logger.info("正在同步服务器时间并刷新token...")

        try:
            # 准备基础签名参数
            curr_token_str = self.current_token.token if self.current_token else ""
            # 如果没有当前token,使用空字符串尝试首次获取

            # 初始偏移尝试 先保留 或许有用
            # initial_adjustment = self.current_token.server_time_offset if self.current_token else -2

            sign, headers = generate_signature(
                token=curr_token_str,
                path="/web/v1/auth/refresh",
                params={},
                dId=self.dId,
                platform=self.platform,
                vName=self.vName,
            )

            # 调用API并获取服务器返回的时间戳进行校准
            new_token, server_offset = await self._call_refresh_api(sign, headers)

            self.current_token = TokenInfo(
                token=new_token, timestamp=int(time.time()), server_time_offset=server_offset
            )
            logger.info(f"Token刷新成功。服务器时间偏移校准为: {server_offset}s")

        except Exception as e:
            logger.error(f"Token刷新或时间同步失败: {e}")
            raise

    async def _call_refresh_api(self, sign: str, headers: dict[str, str]) -> tuple[str, int]:
        """
        核心逻辑:模拟 32.js 的 setSignTime 过程
        """
        # 记录本地发起请求的时间戳 (clientTime)
        client_time = int(time.time())

        request_headers = {
            "Content-Type": "application/json",
            "dId": self.dId,
            "platform": self.platform,
            "sign": sign,
            "timestamp": headers["timestamp"],
            "User-Agent": self.user_agent,
            "vName": self.vName,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.refresh_url, headers=request_headers, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                res_json = await response.json()
                if res_json.get("code") != 0:
                    raise Exception(f"API错误: {res_json.get('message')}")

                token = res_json.get("data", {}).get("token")
                # 提取响应体中的顶级 timestamp (serverTime)
                server_time = res_json.get("timestamp")

                # 计算偏移:serverTime - clientTime
                # 对应 32.js 中的 y (serverTime) 和 A (clientTime) 的逻辑
                offset = 0
                if server_time:
                    offset = int(server_time) - client_time

                return token, offset

    def invalidate_token(self) -> None:
        if self.current_token:
            self.current_token.is_valid = False


# 快捷调用接口
async def get_token_manager(dId: str | None = None, **kwargs) -> SkTokenManager:
    global _default_token_manager
    if "_default_token_manager" not in globals() or _default_token_manager is None:
        if dId is None:
            from shumei_did import get_d_id

            dId = get_d_id()
        _default_token_manager = SkTokenManager(dId=dId, **kwargs)
    return _default_token_manager


async def get_current_token_info() -> TokenInfo | None:
    """获取当前token信息 可能返回None"""
    manager = await get_token_manager()
    return await manager.get_token_info()
