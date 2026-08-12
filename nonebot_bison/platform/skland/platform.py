import asyncio
from collections.abc import Callable
import json
import time
from typing import Any, ClassVar

import httpx
from httpx import AsyncClient
from nonebot.log import logger

from nonebot_bison.platform.platform import NewMessage
from nonebot_bison.post import Post
from nonebot_bison.types import Category, RawPost, Target
from nonebot_bison.utils.site import CookieClientManager, Site

from .day_night_trigger import create_day_night_trigger
from .shumei_did import get_d_id
from .skland_sign import (
    generate_signature_for_item,
    generate_signature_for_user,
    generate_signature_for_user_items,
)
from .skland_token import get_token_manager

SignBuilder = Callable[[str, str], tuple[str, dict[str, str]]]


class SklandClientManager(CookieClientManager):
    _site_name = "skland.com"
    _user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"

    async def get_cookie_name(self, content: str) -> str:
        return "skland"

    async def get_client(self, target: Target | None) -> AsyncClient:
        client = await super().get_client(target)
        client.headers.update({"User-Agent": self._user_agent})
        return client

    @classmethod
    async def get_query_name_client(cls) -> AsyncClient:
        return httpx.AsyncClient(headers={"User-Agent": cls._user_agent})


class SklandSite(Site):
    name = "skland.com"
    schedule_type = create_day_night_trigger(
        base_interval_seconds=180,
        offpeak_multiplier=3,
        jitter_max_seconds=15,
    )
    schedule_setting: ClassVar[dict] = {}
    client_mgr = SklandClientManager


class Skland(NewMessage):
    categories: ClassVar[dict[Category, str]] = {}
    enable_tag = False
    platform_name = "skland"
    name = "森空岛"
    enabled = True
    is_common = True
    site = SklandSite
    has_target = True
    parse_target_promot = "请输入用户ID"

    _max_retries: ClassVar[int] = 2
    _video_extensions: ClassVar[tuple[str, ...]] = (".m3u8", ".mp4", ".mov", ".webm", ".mkv")
    _user_agent: ClassVar[str] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"

    _session_did: ClassVar[str | None] = None
    _session_token: ClassVar[str | None] = None
    _session_token_hour: ClassVar[int | None] = None
    _session_created_at: ClassVar[float | None] = None
    _session_lock: ClassVar[asyncio.Lock | None] = None

    @classmethod
    def _get_session_lock(cls) -> asyncio.Lock:
        if cls._session_lock is None:
            cls._session_lock = asyncio.Lock()
        return cls._session_lock

    @classmethod
    def _get_current_token_hour(cls) -> int:
        return int(time.time() // 3600)

    @classmethod
    async def _generate_new_session(cls) -> tuple[str, str]:
        d_id = get_d_id()
        token_manager = await get_token_manager(dId=d_id)
        token = await token_manager.get_token(force_refresh=True)
        return d_id, token

    @classmethod
    async def _invalidate_session(cls) -> None:
        async with cls._get_session_lock():
            cls._session_did = None
            cls._session_token = None
            cls._session_token_hour = None
            cls._session_created_at = None

    @classmethod
    async def _get_or_refresh_session(cls, force_refresh: bool = False) -> tuple[str | None, str | None]:
        async with cls._get_session_lock():
            current_hour = cls._get_current_token_hour()
            need_refresh = (
                force_refresh
                or not cls._session_did
                or not cls._session_token
                or cls._session_token_hour != current_hour
            )

            if need_refresh:
                cls._session_did, cls._session_token = await cls._generate_new_session()
                cls._session_token_hour = current_hour
                cls._session_created_at = time.time()

            return cls._session_did, cls._session_token

    @classmethod
    def _create_http_client(cls, http2: bool = True) -> AsyncClient:
        return httpx.AsyncClient(http2=http2, headers={"User-Agent": cls._user_agent})

    @staticmethod
    def _build_common_headers(headers: dict, sign: str, d_id: str) -> dict:
        return {
            **headers,
            "sign": sign,
            "platform": "3",
            "vName": "1.0.0",
            "dId": d_id,
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Host": "zonai.skland.com",
            "Origin": "https://www.skland.com",
            "Pragma": "no-cache",
            "Referer": "https://www.skland.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Sec-GPC": "1",
            "TE": "trailers",
        }

    @classmethod
    def _build_image_headers(cls) -> dict:
        return {
            "User-Agent": cls._user_agent,
            "Referer": "https://www.skland.com/",
            "Origin": "https://www.skland.com",
            "Accept": "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5",
        }

    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, int | float | bool):
            return str(value)
        return ""

    @classmethod
    def _first_non_empty_str(cls, *values: Any) -> str:
        for value in values:
            text = cls._clean_text(value)
            if text:
                return text
        return ""

    @staticmethod
    def _normalize_timestamp(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        if isinstance(value, int | float):
            number = float(value)
            return number / 1000 if number > 10_000_000_000 else number
        return None

    @classmethod
    def _extract_text_from_slices(cls, text_slices: Any) -> str:
        if not isinstance(text_slices, list):
            return ""

        parts: list[str] = []
        seen: set[str] = set()
        for piece in text_slices:
            if isinstance(piece, str):
                text = piece.strip()
            elif isinstance(piece, dict):
                text = cls._first_non_empty_str(
                    piece.get("c"),
                    piece.get("text"),
                    piece.get("content"),
                    piece.get("desc"),
                    piece.get("title"),
                )
            else:
                text = ""

            if text and text not in seen:
                seen.add(text)
                parts.append(text)

        return "\n".join(parts).strip()

    @classmethod
    def _looks_like_video_url(cls, url: str) -> bool:
        lowered = url.lower()
        return lowered.endswith(cls._video_extensions) or ".m3u8" in lowered or "/video/" in lowered

    @classmethod
    def _collect_image_list_slice_urls(cls, image_list_slice: Any) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()

        if not isinstance(image_list_slice, list):
            return urls

        for entry in image_list_slice:
            candidates: list[str] = []
            if isinstance(entry, str):
                candidates.append(entry)
            elif isinstance(entry, dict):
                for key in ("url", "src", "image", "img"):
                    value = entry.get(key)
                    if isinstance(value, str):
                        candidates.append(value)

            for value in candidates:
                value = value.strip()
                if not value or cls._looks_like_video_url(value):
                    continue
                if value not in seen:
                    seen.add(value)
                    urls.append(value)

        return urls

    @classmethod
    def _extract_cover_urls_from_value(cls, value: Any) -> list[str]:
        urls: list[str] = []

        if isinstance(value, str):
            urls.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    urls.append(item)
                elif isinstance(item, dict):
                    for key in ("url", "src", "image", "img"):
                        field = item.get(key)
                        if isinstance(field, str):
                            urls.append(field)
        elif isinstance(value, dict):
            for key in ("url", "src", "image", "img"):
                field = value.get(key)
                if isinstance(field, str):
                    urls.append(field)

        return urls

    @classmethod
    def _collect_video_cover_urls(cls, video_list_slice: Any) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()

        if not isinstance(video_list_slice, list):
            return urls

        for entry in video_list_slice:
            if not isinstance(entry, dict):
                continue

            for cover_url in cls._extract_cover_urls_from_value(entry.get("cover")):
                cover_url = cover_url.strip()
                if not cover_url or cls._looks_like_video_url(cover_url):
                    continue
                if cover_url not in seen:
                    seen.add(cover_url)
                    urls.append(cover_url)

        return urls

    @classmethod
    def _extract_images_from_item(cls, item: dict, data: dict) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()

        for source in (item, data):
            if not isinstance(source, dict):
                continue

            for url in cls._collect_image_list_slice_urls(source.get("imageListSlice")):
                if url not in seen:
                    seen.add(url)
                    urls.append(url)

            for url in cls._collect_video_cover_urls(source.get("videoListSlice")):
                if url not in seen:
                    seen.add(url)
                    urls.append(url)

        return urls

    @staticmethod
    def _truncate_text(text: str, limit: int = 1000) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return text[:limit] + "..."

    @classmethod
    async def _signed_get_json(
        cls,
        *,
        url: str,
        params: dict[str, str],
        sign_builder: SignBuilder,
        timeout: float,
        log_prefix: str,
    ) -> dict | None:
        retry_count = 0
        last_error = ""
        last_response_content = ""

        while retry_count <= cls._max_retries:
            try:
                d_id, token = await cls._get_or_refresh_session(force_refresh=False)

                # 添加检查
                if d_id is None or token is None:
                    raise RuntimeError("Failed to get session credentials (d_id or token is None)")

                sign, headers = sign_builder(token, d_id)
                full_headers = cls._build_common_headers(headers, sign, d_id)

                async with cls._create_http_client(http2=True) as client:
                    response = await client.get(url, params=params, headers=full_headers, timeout=timeout)

                response_text = cls._truncate_text(response.text)
                last_response_content = response_text

                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    if response.status_code in (401, 403) and retry_count < cls._max_retries:
                        retry_count += 1
                        await cls._invalidate_session()
                        continue

                    logger.error(f"[Skland] {log_prefix} 失败: {last_error}, 响应内容: {response_text}")
                    return None

                payload = response.json()
                if payload.get("code") != 0:
                    last_error = f"code={payload.get('code')}, message={payload.get('message')}"
                    last_response_content = cls._truncate_text(json.dumps(payload, ensure_ascii=False))

                    if payload.get("code") in (401, 403, 10001) and retry_count < cls._max_retries:
                        retry_count += 1
                        await cls._invalidate_session()
                        continue

                    logger.error(f"[Skland] {log_prefix} 失败: {last_error}, 响应内容: {last_response_content}")
                    return None

                return payload

            except httpx.TimeoutException as e:
                last_error = f"超时错误: {e}"
                if retry_count < cls._max_retries:
                    retry_count += 1
                    continue

            except httpx.NetworkError as e:
                last_error = f"网络错误: {e}"
                if retry_count < cls._max_retries:
                    retry_count += 1
                    continue

            except json.JSONDecodeError as e:
                last_error = f"JSON解析错误: {e}"
                break

            except Exception as e:
                last_error = f"未知错误: {e}"
                if retry_count < cls._max_retries:
                    retry_count += 1
                    continue

                break

        logger.error(f"[Skland] {log_prefix} 失败: {last_error}, 响应内容: {last_response_content or '(无响应内容)'}")
        return None

    @classmethod
    async def _fetch_user_nickname(cls, user_id: str) -> str | None:
        payload = await cls._signed_get_json(
            url="https://zonai.skland.com/web/v1/user",
            params={"id": user_id},
            sign_builder=lambda token, d_id: generate_signature_for_user(
                token=token,
                userId=user_id,
                dId=d_id,
            ),
            timeout=10.0,
            log_prefix=f"获取用户 {user_id} 昵称",
        )
        if not payload:
            return None

        user_data = payload.get("data", {}) or {}
        user_info = user_data.get("user", {}) or {}
        return user_info.get("nickname")

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        _ = client
        return await cls._fetch_user_nickname(str(target))

    @classmethod
    async def parse_target(cls, target_text: str) -> Target:
        if target_text.isdigit():
            return Target(target_text)
        raise cls.ParseTargetException("请输入数字ID")

    def _convert_to_post_format(self, item_data: dict) -> dict | None:
        try:
            item = item_data.get("item", {}) or {}
            user = item_data.get("user", {}) or {}

            post_id = item.get("id", "")
            if not post_id:
                return None

            title = item.get("title", "")
            content = self._extract_text_from_slices(item.get("textSlice"))
            if not content:
                content = title

            created_at = self._normalize_timestamp(item.get("publishedAtTs", time.time())) or time.time()

            return {
                "id": post_id,
                "title": title,
                "content": content,
                "created_at": created_at,
                "images": [],
                "author": {
                    "id": user.get("id", ""),
                    "name": user.get("nickname"),
                },
            }
        except Exception:
            return None

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        user_id = str(target)
        params = {
            "pageSize": "10",
            "userId": user_id,
            "sortType": "2",
        }
        payload = await self._signed_get_json(
            url="https://zonai.skland.com/web/v1/user/items",
            params=params,
            sign_builder=lambda token, d_id: generate_signature_for_user_items(
                token=token,
                userId=user_id,
                pageSize=params["pageSize"],
                sortType=params["sortType"],
                dId=d_id,
            ),
            timeout=10.0,
            log_prefix=f"抓取用户 {user_id} 动态列表",
        )
        if not payload:
            return []

        items_list = payload.get("data", {}).get("list", [])
        nickname = ""
        if items_list:
            user_info = items_list[0].get("user", {}) or {}
            nickname = user_info.get("nickname", "")

        posts: list[RawPost] = []
        post_ids: list[str] = []
        for item_data in items_list:
            post = self._convert_to_post_format(item_data)
            if post:
                posts.append(post)
                post_ids.append(post.get("id", "unknown"))

        latest_ids = post_ids[:3]
        logger.info(
            f"[Skland] 正在抓取: {nickname or '未知用户'} ({user_id}), 动态数: {len(posts)}, 最新ID: {latest_ids}"
        )
        return posts

    async def _fetch_item_detail(self, item_id: str) -> dict | None:
        payload = await self._signed_get_json(
            url="https://zonai.skland.com/web/v1/item",
            params={"id": item_id},
            sign_builder=lambda token, d_id: generate_signature_for_item(
                token=token,
                itemId=item_id,
                dId=d_id,
            ),
            timeout=10.0,
            log_prefix=f"获取动态详情 {item_id}",
        )
        if not payload:
            return None

        try:
            data = payload.get("data", {}) or {}
            item = data.get("item") or data.get("post") or data
            if not isinstance(item, dict):
                item = {}

            user = data.get("user") or item.get("user") or {}
            if not isinstance(user, dict):
                user = {}

            title = self._first_non_empty_str(item.get("title"), data.get("title"))
            content = self._extract_text_from_slices(item.get("textSlice"))
            if not content:
                content = self._extract_text_from_slices(data.get("textSlice"))
            if not content:
                content = title

            raw_ts = (
                item.get("publishedAtTs")
                or item.get("createdAt")
                or item.get("created_at")
                or data.get("publishedAtTs")
                or data.get("createdAt")
            )
            created_at = self._normalize_timestamp(raw_ts) or time.time()
            images = self._extract_images_from_item(item, data)

            return {
                "id": self._first_non_empty_str(item.get("id"), data.get("id"), item_id),
                "title": title,
                "content": content,
                "created_at": created_at,
                "images": images,
                "author": {
                    "id": self._first_non_empty_str(user.get("id"), item.get("userId"), data.get("userId")),
                    "name": self._first_non_empty_str(user.get("nickname"), user.get("name"), item.get("nickname")),
                },
            }
        except Exception:
            return None

    def get_id(self, post: RawPost) -> Any:
        return str(post.get("id", "unknown"))

    def get_date(self, post: RawPost) -> float:
        created_at = post.get("created_at", time.time())
        if isinstance(created_at, str) and created_at.isdigit():
            created_at = int(created_at)
        if isinstance(created_at, int | float) and float(created_at) > 10_000_000_000:
            return float(created_at) / 1000
        return float(created_at)

    async def _process_image(self, image_url: str) -> bytes | None:
        try:
            async with self._create_http_client(http2=True) as client:
                resp = await client.get(image_url, headers=self._build_image_headers(), timeout=10.0)
                if resp.status_code == 200:
                    return resp.content
        except Exception:
            pass
        return None

    async def parse(self, post: RawPost) -> Post:
        post_id = self.get_id(post)
        if post_id and post_id != "unknown":
            detail_post = await self._fetch_item_detail(post_id)
            if detail_post:
                post = {
                    **post,
                    **detail_post,
                    "author": detail_post.get("author") or post.get("author", {}),
                }

        author_info = post.get("author", {}) or {}
        user_id = author_info.get("id", "")
        nickname = author_info.get("name")

        if not nickname and user_id:
            nickname = await self._fetch_user_nickname(user_id)

        if not nickname:
            nickname = f"用户{user_id[-6:]}" if len(user_id) > 6 else f"用户{user_id}"

        images: list[bytes] = []
        raw_images = post.get("images", [])
        if raw_images and isinstance(raw_images, list):
            for img_url in raw_images:
                if not isinstance(img_url, str) or not img_url:
                    continue
                img_bytes = await self._process_image(img_url)
                if img_bytes:
                    images.append(img_bytes)

        content = post.get("content", "")
        if not content:
            content = post.get("title", "无内容")

        return Post(
            self,
            content=content,
            title=post.get("title"),
            # url=post.get("url"),
            images=images if images else None,
            nickname=nickname,
            timestamp=self.get_date(post),
        )
