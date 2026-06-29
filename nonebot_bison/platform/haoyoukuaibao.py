import asyncio
import base64
from collections.abc import Collection
from datetime import datetime, timedelta
import hashlib
import re
from typing import Any, ClassVar

from httpx import AsyncClient, HTTPStatusError, NetworkError, TimeoutException
from nonebot.log import logger

from nonebot_bison.post import Post
from nonebot_bison.types import Category, RawPost, Tag, Target
from nonebot_bison.utils import http_client
from nonebot_bison.utils.site import Site

from .platform import NewMessage

_HEADER = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
    "origin": "https://www.3839.com",
    "referer": "https://www.3839.com/",
}

MAX_RETRY_MINUTES = 30
RETRY_INTERVAL = 180


class SkipPostException(Exception):
    pass


class RetryPost:
    def __init__(self, post: RawPost, target: str):
        self.post = dict(post)
        self.target = target
        self.first_seen = datetime.now()
        self.retry_count = 0
        self.next_retry = datetime.now() + timedelta(seconds=RETRY_INTERVAL)
        self.post_id = str(post.get("id"))

    def should_retry(self) -> bool:
        if datetime.now() - self.first_seen > timedelta(minutes=MAX_RETRY_MINUTES):
            return False
        return datetime.now() >= self.next_retry

    def update_next_retry(self):
        self.retry_count += 1
        self.next_retry = datetime.now() + timedelta(seconds=RETRY_INTERVAL)

    def is_expired(self) -> bool:
        return datetime.now() - self.first_seen > timedelta(minutes=MAX_RETRY_MINUTES)


class HykbDeepScraper:
    FIXED_SALT: str = "Nfb2nIcOmeSx7ltv"

    @classmethod
    def _extract_waf_seed(cls, html: str) -> str | None:
        pattern = r'[A-Za-z]{3,}\s*\(\s*["\']([A-Za-z0-9+/=]{40,})["\']\s*\)'
        match = re.search(pattern, html)
        if match:
            return match.group(1)

        for script in re.findall(r"<script[^>]*>(.*?)</script>", html, re.S):
            match = re.search(r'["\']([A-Za-z0-9+/=]{40,}={0,2})["\']', script)
            if match:
                candidate = match.group(1)
                try:
                    decoded = base64.b64decode(candidate).decode("utf-8")
                    if "|" in decoded and len(decoded.split("|")) >= 3:
                        return candidate
                except Exception:
                    continue
        return None

    @classmethod
    async def get_html_with_waf(cls, url: str) -> str | None:
        async with AsyncClient(headers=_HEADER, follow_redirects=True, timeout=30.0) as client:
            try:
                res = await client.get(url)
                if res.status_code != 200:
                    return None

                has_doccon = "docCon" in res.text
                has_doctop = "docTop" in res.text
                seed_encoded = cls._extract_waf_seed(res.text)

                if not seed_encoded:
                    if has_doccon or has_doctop:
                        return res.text
                    else:
                        return None

                try:
                    seed_decoded = base64.b64decode(seed_encoded).decode("utf-8")
                    seed = seed_decoded.split("|")
                    if len(seed) < 4:
                        return None

                    md5_input = (seed[0] + seed[2] + seed[3] + cls.FIXED_SALT).encode("utf-8")
                    md5_val = hashlib.md5(md5_input).hexdigest()

                    cookie_name_secret = f"bbs_{seed[1]}_secret_{seed[0]}"
                    cookie_name_transfer = f"bbs_{seed[1]}_transfer_{seed[0]}"
                    cookie_value = f"{md5_val}|{seed[3]}"

                    client.cookies.set(cookie_name_secret, cookie_value, domain="bbs.3839.com")
                    client.cookies.set(cookie_name_transfer, "1", domain="bbs.3839.com")
                    client.headers.update({"Referer": url})

                    await asyncio.sleep(0.5)
                    final_res = await client.get(url)

                    if final_res.status_code == 200:
                        if "docCon" in final_res.text or "docTop" in final_res.text:
                            return final_res.text
                        else:
                            return None
                    else:
                        return None
                except Exception:
                    return None
            except (TimeoutException, NetworkError, HTTPStatusError):
                return None
            except Exception:
                return None

    @classmethod
    def _extract_with_depth(cls, html: str, start_marker: str) -> str | None:
        start = html.find(start_marker)
        if start == -1:
            base_class = start_marker.split('"')[1] if '"' in start_marker else start_marker.split("'")[1]
            pattern = rf'<div\s+class="{base_class}"[^>]*>'
            match = re.search(pattern, html)
            if not match:
                return None
            start = match.start()
            start_marker = match.group()

        tag_end = html.find(">", start)
        if tag_end == -1:
            return None

        pos = tag_end + 1
        depth = 1

        while pos < len(html) and depth > 0:
            next_open = html.find("<div", pos)
            next_close = html.find("</div>", pos)

            if next_close == -1:
                return html[start:pos]

            if next_open != -1 and next_open < next_close:
                after = html[next_open + 4 : next_open + 5] if next_open + 4 < len(html) else ""
                if after in (" ", ">", "\n", "\r", "\t", '"', "'"):
                    depth += 1
                pos = next_open + 4
            else:
                depth -= 1
                if depth == 0:
                    return html[start : next_close + 6]
                pos = next_close + 6

        return None

    @classmethod
    def _extract_div_by_class(cls, html: str, class_name: str) -> str | None:
        if not html:
            return None
        return cls._extract_with_depth(html, f'<div class="{class_name}">')

    @classmethod
    def _remove_div_by_class(cls, html: str, class_name: str) -> str:
        pattern = rf'<div\s+class="{class_name}"[^>]*>.*?</div>\s*</div>'
        result = re.sub(pattern, "", html, flags=re.S)
        if class_name == "panel-game":
            result = re.sub(r'\s*<a\s+class="btn\s+btnG"[^>]*>[^<]*</a>', "", result)
        return result

    @classmethod
    def extract_content(cls, html: str) -> str:
        if not html:
            return ""

        doccon_html = cls._extract_div_by_class(html, "docCon")
        if not doccon_html:
            return ""

        doccon_clean = re.sub(r'<div\s+class="title"[^>]*>.*?</div>', "", doccon_html, flags=re.S)
        doccon_clean = re.sub(r'<div\s+class="content"[^>]*>.*?</div>', "", doccon_clean, flags=re.S)
        doccon_clean = re.sub(r'<div\s+class="detail"[^>]*>.*?</div>', "", doccon_clean, flags=re.S)

        doccon_clean = cls._remove_div_by_class(doccon_clean, "panel-game")
        doccon_clean = re.sub(r'<div\s+class="pic"[^>]*>.*?</div>', "", doccon_clean, flags=re.S)

        doccon_clean = re.sub(r"<div>★马上在快爆下载[^<]*</div>", "", doccon_clean)

        text_parts: list[str] = []

        all_divs = re.findall(r"<div[^>]*>(.*?)</div>", doccon_clean, re.S)
        for div_content in all_divs:
            if not div_content or not div_content.strip():
                continue

            clean_text = re.sub(r"<[^>]+>", "", div_content)
            for html_entity in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')]:
                clean_text = clean_text.replace(html_entity[0], html_entity[1])
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

            if clean_text and len(clean_text) > 1:
                if "快爆下载" not in clean_text and "抢先获一手" not in clean_text:
                    text_parts.append(clean_text)

        if not text_parts:
            all_text = re.sub(r"<[^>]+>", "\n", doccon_clean)
            all_text = re.sub(r"&nbsp;", " ", all_text)
            for line in all_text.split("\n"):
                line = line.strip()
                if line and len(line) > 1:
                    if "快爆下载" not in line and "抢先获一手" not in line:
                        text_parts.append(line)

        return "\n".join(text_parts) if text_parts else ""

    @classmethod
    def _is_irrelevant_image(cls, url: str) -> bool:
        url_lower = url.lower()

        size_match = re.search(r"/(\d+)x(\d+)\.(jpg|png|gif|webp)", url_lower)
        if size_match:
            width = int(size_match.group(1))
            height = int(size_match.group(2))
            if width <= 50 or height <= 50:
                return True

        icon_patterns = [
            "favicon",
            "logo",
            "icon",
            "avatar",
            "emoji",
            "avator",
            "ident-",
            "ico",
            "user/",
            "/user/",
            "default_avatar",
            "noavatar",
        ]
        for pattern in icon_patterns:
            if pattern in url_lower:
                return True

        if url.startswith("data:image/"):
            return True

        return False

    @classmethod
    def _process_url(cls, url: str) -> str:
        if url.startswith("//"):
            return f"https:{url}"
        elif url.startswith("/"):
            return f"https://bbs.3839.com{url}"
        return url

    @classmethod
    def extract_images(cls, html: str) -> list[str]:
        if not html:
            return []

        seen = set()
        ordered = []

        def add_image(url: str):
            if not url:
                return
            processed = cls._process_url(url)
            if processed in seen or cls._is_irrelevant_image(processed):
                return
            seen.add(processed)
            ordered.append(processed)

        doctop_html = cls._extract_div_by_class(html, "docTop")
        if doctop_html:
            video_poster = re.search(r'<video[^>]+poster=["\']([^"\']+)["\']', doctop_html, re.S)
            if video_poster:
                add_image(video_poster.group(1))
            else:
                poster_style = re.search(
                    r'class="vjs-poster"[^>]+style="[^"]*url\(&quot;([^&]+?)&quot;\)', doctop_html, re.S
                )
                if poster_style:
                    add_image(poster_style.group(1))

            album_imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', doctop_html, re.S)
            for img_url in album_imgs:
                add_image(img_url)

        doccon_html = cls._extract_div_by_class(html, "docCon")
        if doccon_html:
            pic_imgs = re.findall(r'<div\s+class="pic"[^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']', doccon_html, re.S)
            for img_url in pic_imgs:
                add_image(img_url)

            content_html = cls._extract_div_by_class(doccon_html, "content")
            if content_html:
                video_poster = re.search(
                    r'<div\s+class="video"[^>]*>.*?<video[^>]+poster="([^"]+)"', content_html, re.S
                )
                if video_poster:
                    add_image(video_poster.group(1))

        return ordered


class HaoyoukuaibaoSite(Site):
    name = "3839.com"
    schedule_type = "interval"
    schedule_setting: ClassVar[dict] = {"seconds": 180}
    scheduler_class = "hykb"


class Haoyoukuaibao(NewMessage):
    categories: ClassVar[dict[Category, str]] = {}
    enable_tag = True
    platform_name = "hykb"
    name = "好游快爆"
    enabled = True
    is_common = True
    site = HaoyoukuaibaoSite
    has_target = True

    _user_cache: ClassVar[dict[str, str]] = {}
    _first_fetch_flags: ClassVar[dict[str, bool]] = {}
    _fetched_ids: ClassVar[dict[str, set[str]]] = {}
    _retry_queue: ClassVar[dict[str, RetryPost]] = {}
    _pushed_ids: ClassVar[set[str]] = set()

    @classmethod
    def _make_retry_key(cls, target_str: str, post_id: Any) -> str:
        return f"{target_str}_{post_id}"

    @classmethod
    async def _fetch_post_detail(cls, post_id: str, target_str: str) -> tuple[str, list[str]] | None:
        detail_url = f"https://bbs.3839.com/thread-{post_id}.htm"
        html = await HykbDeepScraper.get_html_with_waf(detail_url)
        if not html:
            return None
        content = HykbDeepScraper.extract_content(html)
        images = HykbDeepScraper.extract_images(html)
        return content, images

    @classmethod
    async def _download_images(cls, image_urls: list[str]) -> list[bytes]:
        pics: list[bytes] = []
        if not image_urls:
            return pics
        async with http_client() as client:
            for url in image_urls:
                try:
                    resp = await client.get(url, headers={"referer": "https://www.3839.com/"}, timeout=30.0)
                    if resp.status_code == 200:
                        pics.append(resp.content)
                except Exception:
                    continue
        return pics

    @classmethod
    def _create_fallback_post(cls, post_id: str, target_str: str, post_obj) -> Post:
        nickname = cls._user_cache.get(target_str, "未知用户")
        detail_url = f"https://bbs.3839.com/thread-{post_id}.htm"
        return Post(
            post_obj,
            content=f"【动态 {post_id}】\n详情页未就绪,请手动查看:\n{detail_url}",
            images=[],
            nickname=nickname,
        )

    @classmethod
    def _should_retry_parse_result(cls, content: str, images: list[str]) -> bool:
        normalized = re.sub(r"\s+", "", content or "")
        content_len = len(normalized)
        if content_len <= 8:
            return True
        tag_patterns = {"官方", "笔记官方", "资讯官方", "攻略官方", "【官方】", "【笔记官方】"}
        if normalized in tag_patterns:
            return True
        return False

    @classmethod
    def _enqueue_retry(cls, raw_post: RawPost, target_str: str, reason: str = "unknown") -> str:
        post_id = raw_post.get("id")
        retry_key = cls._make_retry_key(target_str, post_id)
        if retry_key not in cls._retry_queue:
            cls._retry_queue[retry_key] = RetryPost(dict(raw_post), target_str)
        else:
            cls._retry_queue[retry_key].post = dict(raw_post)
        return retry_key

    @classmethod
    async def _prepare_raw_post(cls, raw_post: RawPost, target_str: str) -> RawPost | None:
        post_id = raw_post.get("id")
        retry_key = cls._make_retry_key(target_str, post_id)

        result = await cls._fetch_post_detail(str(post_id), target_str)

        if not result:
            cls._enqueue_retry(raw_post, target_str, reason="html_fetch_failed")
            return None

        final_content, final_images = result

        if cls._should_retry_parse_result(final_content, final_images):
            cls._enqueue_retry(raw_post, target_str, reason="content_not_ready")
            return None

        prepared_post = dict(raw_post)
        prepared_post["_target"] = target_str
        prepared_post["_final_content"] = final_content
        prepared_post["_final_images"] = final_images
        cls._retry_queue.pop(retry_key, None)

        return prepared_post

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        target_str = str(target)

        if target_str in cls._user_cache:
            return cls._user_cache[target_str]

        try:
            data = {"ac": "dynamic_home", "vuid": target_str, "last_id": "", "cursor": ""}
            resp = await client.post(
                "https://www.3839.com/app/hykb_web/api/api_user.php", data=data, headers=_HEADER, timeout=10.0
            )
            if resp.status_code != 200:
                return None

            res_json = resp.json()
            dynamics = res_json.get("result", {}).get("data", [])

            if dynamics:
                nickname = dynamics[0].get("user", {}).get("nickname")
                if nickname:
                    cls._user_cache[target_str] = nickname
                    return nickname

            return None
        except Exception:
            return None

    @classmethod
    async def parse_target(cls, target_text: str) -> Target:
        if re.fullmatch(r"\d+", target_text):
            return Target(target_text)
        elif match := re.search(r"vuid[=/](\d+)", target_text):
            return Target(match.group(1))
        else:
            raise cls.ParseTargetException("正确格式:\n1. 用户数字ID\n2. 用户主页链接")

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        target_str = str(target)
        is_first_fetch = target_str not in self.__class__._first_fetch_flags

        try:
            client = await self.ctx.get_client(target)
            data = {"ac": "dynamic_home", "vuid": target_str, "last_id": "", "cursor": ""}
            res = await client.post(
                "https://www.3839.com/app/hykb_web/api/api_user.php", data=data, headers=_HEADER, timeout=15.0
            )

            res_json = res.json()
            dynamics = res_json.get("result", {}).get("data", [])

            if dynamics:
                latest_ids = [str(d.get("id")) for d in dynamics[:5] if d.get("id")]
                logger.info(f"[3839] 用户 {target_str} 最新动态ID列表: {latest_ids}")

            if dynamics and target_str not in self.__class__._user_cache:
                nickname = dynamics[0].get("user", {}).get("nickname")
                if nickname:
                    self.__class__._user_cache[target_str] = nickname

            if is_first_fetch:
                self.__class__._fetched_ids[target_str] = {str(d.get("id")) for d in dynamics if d.get("id")}
                self.__class__._first_fetch_flags[target_str] = True
                return []

            if target_str not in self.__class__._fetched_ids:
                self.__class__._fetched_ids[target_str] = set()

            ready_posts: list[RawPost] = []
            expired_keys: list[str] = []

            for d in dynamics:
                d_id = str(d.get("id"))
                if not d_id or d_id in self.__class__._fetched_ids[target_str]:
                    continue

                retry_key = self.__class__._make_retry_key(target_str, d_id)
                if retry_key in self.__class__._retry_queue:
                    continue

                self.__class__._fetched_ids[target_str].add(d_id)
                prepared = await self.__class__._prepare_raw_post({**d, "_target": target_str}, target_str)
                if prepared is not None:
                    ready_posts.append(prepared)

            for key, retry_post in list(self.__class__._retry_queue.items()):
                if retry_post.target != target_str:
                    continue

                push_key = self.__class__._make_retry_key(target_str, retry_post.post_id)
                if push_key in self.__class__._pushed_ids:
                    expired_keys.append(key)
                    continue

                if retry_post.is_expired():
                    retry_post.post["_target"] = target_str
                    retry_post.post["_retry_expired"] = True
                    retry_post.post["_detail_url"] = f"https://bbs.3839.com/thread-{retry_post.post_id}.htm"
                    ready_posts.append(retry_post.post)
                    expired_keys.append(key)
                    continue

                if retry_post.should_retry():
                    retry_post.update_next_retry()
                    prepared = await self.__class__._prepare_raw_post(retry_post.post, target_str)
                    if prepared is not None:
                        ready_posts.append(prepared)

            for key in expired_keys:
                self.__class__._retry_queue.pop(key, None)

            return ready_posts
        except Exception:
            return []

    async def parse(self, raw_post: RawPost) -> Post:
        post_id = raw_post.get("id")
        target_str = raw_post.get("_target", "")
        retry_key = self.__class__._make_retry_key(target_str, post_id)
        nickname = raw_post.get("user", {}).get("nickname") or self.__class__._user_cache.get(target_str, "未知用户")

        if raw_post.get("_retry_expired"):
            self.__class__._retry_queue.pop(retry_key, None)
            self.__class__._pushed_ids.add(retry_key)
            return self.__class__._create_fallback_post(str(post_id), target_str, self)

        final_content = raw_post.get("_final_content")
        final_images = raw_post.get("_final_images", [])

        if final_content is None:
            logger.debug(f"[3839] 动态 {post_id} 缺少内容,加入重试队列")
            self.__class__._enqueue_retry(raw_post, target_str, reason="missing_prepared_data")
            return Post(
                self,
                content=f"【动态 {post_id}】\n详情页尚未刷新完成,已加入延迟重抓队列。",
                images=[],
                nickname=nickname,
            )

        pics = await self.__class__._download_images(final_images)

        self.__class__._retry_queue.pop(retry_key, None)
        self.__class__._pushed_ids.add(retry_key)

        return Post(self, content=final_content, images=pics, nickname=nickname)

    async def process_retry_queue(self) -> list[Post]:
        retry_posts: list[Post] = []
        expired_keys: list[str] = []

        for key, retry_post in list(self.__class__._retry_queue.items()):
            post_id = retry_post.post_id
            target_str = retry_post.target
            push_key = f"{target_str}_{post_id}"

            if push_key in self.__class__._pushed_ids:
                expired_keys.append(key)
                continue

            if retry_post.is_expired():
                post = self.__class__._create_fallback_post(post_id, target_str, self)
                retry_posts.append(post)
                self.__class__._pushed_ids.add(push_key)
                expired_keys.append(key)
                continue

            if retry_post.should_retry():
                result = await self.__class__._fetch_post_detail(post_id, target_str)

                if result:
                    final_content, final_images = result
                    pics = await self.__class__._download_images(final_images)

                    nickname = self.__class__._user_cache.get(target_str, "未知用户")
                    post = Post(self, content=final_content, images=pics, nickname=nickname)
                    retry_posts.append(post)
                    self.__class__._pushed_ids.add(push_key)
                    expired_keys.append(key)
                else:
                    retry_post.update_next_retry()

        for key in expired_keys:
            self.__class__._retry_queue.pop(key, None)

        return retry_posts

    def get_id(self, post: RawPost) -> Any:
        return f"{post.get('_target')}_{post.get('id')}"

    def get_date(self, post: RawPost) -> float:
        return datetime.now().timestamp()

    def get_category(self, post: RawPost) -> Category:
        return Category(1)

    def get_tags(self, post: RawPost) -> Collection[Tag] | None:
        return None
